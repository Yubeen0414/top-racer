"""차량 물리와 그리기.

heading(라디안): 0 = 오른쪽, 화면 y가 아래로 커지니까 값이 커지면 시계 방향으로 돌아요.
속도는 '앞 방향 성분'과 '옆 방향 성분'으로 나눠서 계산해요.
옆 성분을 천천히 없애는 게 미끄러짐(드리프트)의 핵심이에요.

드리프트: 빠르게 달리면서 B와 조향을 같이 누르면 시작.
  접지력이 낮아지고 더 많이 돌아서 차가 옆으로 미끄러져요.
  옆으로 미끄러지며 잃는 속도 대부분을 앞으로 되돌려줘서 속도를 유지하며 길게 미끄러질 수 있어요.
  미끄러지는 동안 부스트 게이지가 차요 (옆으로 많이 미끄러질수록 빨리).
  드리프트 중엔 B가 브레이크로 동작하지 않고, 드리프트가 끝난 뒤에도 B를 한 번 떼기 전까지는
  브레이크/후진이 안 걸려요 (B를 계속 누르고 있다가 갑자기 후진하지 않게).
  조향을 잠깐 넘게 놓거나 너무 느려지면 끝나요. 잔디/벽에 닿으면 게이지를 잃어요.
부스트: 게이지가 1칸 이상일 때 위(up)를 누르면 BOOST_SEC 동안 더 빨라져요.
"""
import math

from PIL import Image, ImageDraw

import config
from track import WALL, GRASS, SAND


def _make_sprites(color, alpha=255, shadow=True):
    L, W = config.CAR_LENGTH, config.CAR_WIDTH

    body = Image.new("RGBA", (L, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    d.rounded_rectangle((0, 0, L - 1, W - 1), radius=3, fill=color + (255,), outline=(20, 20, 20, 255))
    d.rectangle((L - 9, 2, L - 6, W - 3), fill=(150, 200, 255, 255))   # 앞 유리 (오른쪽이 앞)
    d.rectangle((3, 3, 5, W - 4), fill=(110, 150, 200, 255))           # 뒷 유리
    d.line((7, W // 2, L - 11, W // 2), fill=(255, 255, 255, 255))     # 줄무늬
    if alpha < 255:
        body.putalpha(body.getchannel("A").point(lambda a: a * alpha // 255))

    sh = Image.new("RGBA", (L, W), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((0, 0, L - 1, W - 1), radius=3, fill=(0, 0, 0, 90))

    # 매 프레임 rotate()는 느리니까 시작할 때 한 번에 만들어 둬요.
    sprites, shadows = [], []
    for i in range(config.ROTATION_STEPS):
        deg = -i * 360 / config.ROTATION_STEPS
        sprites.append(body.rotate(deg, resample=Image.BICUBIC, expand=True))
        if shadow:
            shadows.append(sh.rotate(deg, resample=Image.BICUBIC, expand=True))
    return sprites, shadows


def sprite_index(heading):
    return round(heading / (2 * math.pi) * config.ROTATION_STEPS) % config.ROTATION_STEPS


_ghost_sprites = None


def ghost_sprites():
    """고스트용 반투명 파란 차 (64방향). 처음 쓸 때 한 번만 만들어요."""
    global _ghost_sprites
    if _ghost_sprites is None:
        _ghost_sprites, _ = _make_sprites((90, 170, 255), alpha=config.GHOST_ALPHA, shadow=False)
    return _ghost_sprites


class Car:
    _sprites = None
    _shadows = None

    def __init__(self, x, y, heading):
        if Car._sprites is None:
            Car._sprites, Car._shadows = _make_sprites((230, 50, 40))
        self.gauge = 0.0          # 부스트 게이지 (0 ~ BOOST_SEGMENTS 칸)
        self.reset(x, y, heading)

    def reset(self, x, y, heading):
        """위치/속도 초기화. 게이지는 유지 (체크포인트 복귀해도 모은 게이지는 남게)."""
        self.x, self.y = float(x), float(y)
        self.heading = heading
        self.vx = self.vy = 0.0
        self.on_grass = False
        self.on_sand = False
        self.drifting = False
        self.no_steer_time = 0.0  # 드리프트 중 조향을 놓고 있던 시간
        self.b_lock = False       # 드리프트에 쓴 B를 아직 안 뗐으면 True (브레이크 막기)
        self.boost_time = 0.0

    @property
    def speed(self):
        return math.hypot(self.vx, self.vy)

    @property
    def boosting(self):
        return self.boost_time > 0

    def forward_speed(self):
        return self.vx * math.cos(self.heading) + self.vy * math.sin(self.heading)

    # ---------- 물리 ----------
    def update(self, dt, inp, track):
        f_old = self.forward_speed()
        steer = int(inp.held("right")) - int(inp.held("left"))

        # 0) 드리프트 시작/끝, 부스트 시작
        if not inp.held("b"):
            self.b_lock = False
        if not self.drifting:
            # B와 조향을 같이 누른 순간 (어느 쪽을 먼저 눌러도 돼요)
            just = inp.pressed("b") or inp.pressed("left") or inp.pressed("right")
            if steer and inp.held("b") and just and f_old > config.DRIFT_MIN_SPEED:
                self.drifting = True
                self.b_lock = True
                self.no_steer_time = 0.0
        else:
            self.no_steer_time = 0.0 if steer else self.no_steer_time + dt
            if self.no_steer_time > config.DRIFT_RELEASE_GRACE or self.speed < config.DRIFT_END_SPEED:
                self.drifting = False

        if inp.pressed("up") and not self.boosting and self.gauge >= 1.0:
            self.gauge -= 1.0
            self.boost_time = config.BOOST_SEC

        # 1) 조향: 속도가 있을 때만, 후진이면 반대로. 드리프트 중엔 더 많이 돌아요.
        if steer:
            factor = min(1.0, abs(f_old) / config.TURN_FULL_SPEED)
            direction = 1 if f_old >= 0 else -1
            rate = config.TURN_RATE * (config.DRIFT_TURN_MULT if self.drifting else 1.0)
            self.heading = (self.heading + steer * rate * factor * direction * dt) % (2 * math.pi)

        # 2) 새 방향 기준으로 속도를 앞/옆 성분으로 분해
        fx, fy = math.cos(self.heading), math.sin(self.heading)
        rx, ry = -fy, fx
        f = self.vx * fx + self.vy * fy
        lat = self.vx * rx + self.vy * ry

        # 3) 가속 / 브레이크 / 후진 / 부스트
        if inp.held("a"):
            f += config.ACCEL * dt
        elif inp.held("b") and not self.b_lock:      # 드리프트에 쓴 B는 떼기 전까지 무시
            f -= (config.BRAKE if f > 5 else config.REVERSE_ACCEL) * dt
        if self.boosting:
            self.boost_time = max(0.0, self.boost_time - dt)
            f += config.BOOST_ACCEL * dt

        # 4) 노면: 잔디면 느려지고, 모래면 훨씬 느려짐
        surface = track.surface_at(self.x, self.y)
        self.on_sand = surface == SAND
        self.on_grass = surface == GRASS or self.on_sand   # '도로 밖' (게이지 손실, HUD 색)
        drag = config.DRAG
        if self.on_sand:
            drag += config.SAND_DRAG
            max_f = config.SAND_MAX_SPEED
        elif self.on_grass:
            drag += config.GRASS_DRAG
            max_f = config.GRASS_MAX_SPEED
        else:
            max_f = config.MAX_SPEED * (config.BOOST_SPEED_MULT if self.boosting else 1.0)
        f *= math.exp(-drag * dt)
        if f > max_f:
            f -= (f - max_f) * min(1.0, 4.0 * dt)   # 갑자기 멈추지 않게 서서히
        f = max(-config.MAX_REVERSE, f)

        # 5) 접지력: 옆으로 미끄러지는 속도를 줄임
        if self.drifting:
            # 드리프트 중엔 조금만 줄이고, 줄어든 만큼의 대부분을 앞 방향 속도로 돌려줘요
            new_lat = lat * math.exp(-config.DRIFT_GRIP * dt)
            if f > 0:
                f += abs(lat - new_lat) * config.DRIFT_KEEP
            lat = new_lat
        else:
            lat *= math.exp(-config.GRIP * dt)

        # 부스트 게이지: 드리프트 중 옆으로 미끄러지는 정도만큼 충전
        if self.drifting:
            if self.on_grass:
                self.gauge -= config.BOOST_GRASS_LOSS * dt
            else:
                speed = math.hypot(f, lat)
                if speed > 1.0:
                    slip = abs(lat) / speed
                    self.gauge += config.BOOST_CHARGE * min(1.0, slip / config.DRIFT_SLIP_FULL) * dt

        self.vx = f * fx + lat * rx
        self.vy = f * fy + lat * ry

        # 6) 이동 + 벽 충돌 (x, y 따로 검사해서 벽을 따라 미끄러지게)
        hit = False
        nx = self.x + self.vx * dt
        if self._blocked(track, nx, self.y):
            self.vx = -self.vx * config.WALL_BOUNCE
            hit = True
        else:
            self.x = nx
        ny = self.y + self.vy * dt
        if self._blocked(track, self.x, ny):
            self.vy = -self.vy * config.WALL_BOUNCE
            hit = True
        else:
            self.y = ny
        if hit and self.drifting:
            self.gauge -= config.BOOST_WALL_LOSS
            self.drifting = False

        self.gauge = min(max(self.gauge, 0.0), float(config.BOOST_SEGMENTS))

    @staticmethod
    def _blocked(track, x, y):
        r = config.CAR_WIDTH / 2
        for dx, dy in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r)):
            if track.surface_at(x + dx, y + dy) == WALL:
                return True
        return False

    # ---------- 그리기 ----------
    def draw(self, frame, cam_x, cam_y, flicker=0):
        idx = sprite_index(self.heading)
        spr, sh = Car._sprites[idx], Car._shadows[idx]
        cx, cy = self.x - cam_x, self.y - cam_y

        if self.boosting:   # 차 뒤 불꽃
            back = config.CAR_LENGTH / 2 + 4
            bx, by = cx - math.cos(self.heading) * back, cy - math.sin(self.heading) * back
            r = 5 if flicker % 2 == 0 else 4
            d = ImageDraw.Draw(frame)
            d.ellipse((bx - r, by - r, bx + r, by + r), fill=(255, 120, 0))
            d.ellipse((bx - 2, by - 2, bx + 2, by + 2), fill=(255, 240, 120))

        sx, sy = int(cx - spr.width / 2), int(cy - spr.height / 2)
        frame.paste(sh, (sx + 2, sy + 3), sh)
        frame.paste(spr, (sx, sy), spr)
