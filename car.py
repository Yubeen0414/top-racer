"""차량 물리와 그리기.

heading(라디안): 0 = 오른쪽, 화면 y가 아래로 커지니까 값이 커지면 시계 방향으로 돌아요.
속도는 '앞 방향 성분'과 '옆 방향 성분'으로 나눠서 계산해요.
옆 성분을 천천히 없애는 게 미끄러짐(드리프트)의 핵심이에요.
"""
import math

from PIL import Image, ImageDraw

import config
from track import WALL, GRASS


def _make_sprites():
    L, W = config.CAR_LENGTH, config.CAR_WIDTH

    body = Image.new("RGBA", (L, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    d.rounded_rectangle((0, 0, L - 1, W - 1), radius=3, fill=(230, 50, 40, 255), outline=(20, 20, 20, 255))
    d.rectangle((L - 9, 2, L - 6, W - 3), fill=(150, 200, 255, 255))   # 앞 유리 (오른쪽이 앞)
    d.rectangle((3, 3, 5, W - 4), fill=(110, 150, 200, 255))           # 뒷 유리
    d.line((7, W // 2, L - 11, W // 2), fill=(255, 255, 255, 255))     # 줄무늬

    shadow = Image.new("RGBA", (L, W), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((0, 0, L - 1, W - 1), radius=3, fill=(0, 0, 0, 90))

    # 매 프레임 rotate()는 느리니까 시작할 때 한 번에 만들어 둬요.
    sprites, shadows = [], []
    for i in range(config.ROTATION_STEPS):
        deg = -i * 360 / config.ROTATION_STEPS
        sprites.append(body.rotate(deg, resample=Image.BICUBIC, expand=True))
        shadows.append(shadow.rotate(deg, resample=Image.BICUBIC, expand=True))
    return sprites, shadows


class Car:
    _sprites = None
    _shadows = None

    def __init__(self, x, y, heading):
        if Car._sprites is None:
            Car._sprites, Car._shadows = _make_sprites()
        self.reset(x, y, heading)

    def reset(self, x, y, heading):
        self.x, self.y = float(x), float(y)
        self.heading = heading
        self.vx = self.vy = 0.0
        self.on_grass = False

    @property
    def speed(self):
        return math.hypot(self.vx, self.vy)

    def forward_speed(self):
        return self.vx * math.cos(self.heading) + self.vy * math.sin(self.heading)

    # ---------- 물리 ----------
    def update(self, dt, inp, track):
        # 1) 조향: 속도가 있을 때만, 후진이면 반대로
        f_old = self.forward_speed()
        steer = int(inp.held("right")) - int(inp.held("left"))
        if steer:
            factor = min(1.0, abs(f_old) / config.TURN_FULL_SPEED)
            direction = 1 if f_old >= 0 else -1
            self.heading = (self.heading + steer * config.TURN_RATE * factor * direction * dt) % (2 * math.pi)

        # 2) 새 방향 기준으로 속도를 앞/옆 성분으로 분해
        fx, fy = math.cos(self.heading), math.sin(self.heading)
        rx, ry = -fy, fx
        f = self.vx * fx + self.vy * fy
        lat = self.vx * rx + self.vy * ry

        # 3) 가속 / 브레이크 / 후진
        if inp.held("a"):
            f += config.ACCEL * dt
        elif inp.held("b"):
            f -= (config.BRAKE if f > 5 else config.REVERSE_ACCEL) * dt

        # 4) 노면: 잔디면 더 느려짐
        self.on_grass = track.surface_at(self.x, self.y) == GRASS
        drag = config.DRAG + (config.GRASS_DRAG if self.on_grass else 0.0)
        f *= math.exp(-drag * dt)
        max_f = config.GRASS_MAX_SPEED if self.on_grass else config.MAX_SPEED
        if f > max_f:
            f -= (f - max_f) * min(1.0, 4.0 * dt)   # 갑자기 멈추지 않게 서서히
        f = max(-config.MAX_REVERSE, f)

        # 5) 접지력: 옆으로 미끄러지는 속도를 줄임
        lat *= math.exp(-config.GRIP * dt)

        self.vx = f * fx + lat * rx
        self.vy = f * fy + lat * ry

        # 6) 이동 + 벽 충돌 (x, y 따로 검사해서 벽을 따라 미끄러지게)
        nx = self.x + self.vx * dt
        if self._blocked(track, nx, self.y):
            self.vx = -self.vx * config.WALL_BOUNCE
        else:
            self.x = nx
        ny = self.y + self.vy * dt
        if self._blocked(track, self.x, ny):
            self.vy = -self.vy * config.WALL_BOUNCE
        else:
            self.y = ny

    @staticmethod
    def _blocked(track, x, y):
        r = config.CAR_WIDTH / 2
        for dx, dy in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r)):
            if track.surface_at(x + dx, y + dy) == WALL:
                return True
        return False

    # ---------- 그리기 ----------
    def draw(self, frame, cam_x, cam_y):
        idx = round(self.heading / (2 * math.pi) * config.ROTATION_STEPS) % config.ROTATION_STEPS
        spr, sh = Car._sprites[idx], Car._shadows[idx]
        sx = int(self.x - cam_x - spr.width / 2)
        sy = int(self.y - cam_y - spr.height / 2)
        frame.paste(sh, (sx + 2, sy + 3), sh)
        frame.paste(spr, (sx, sy), spr)
