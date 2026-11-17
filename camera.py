"""룩어헤드 카메라: 달리는 방향 쪽을 더 보여줘요."""
import math

import config


class Camera:
    def __init__(self, x, y, world_w, world_h):
        self.x, self.y = float(x), float(y)
        self.world_w, self.world_h = world_w, world_h

    def update(self, dt, car):
        # 속도 방향으로 앞당긴 지점을 목표로
        lx, ly = car.vx * config.LOOKAHEAD_TIME, car.vy * config.LOOKAHEAD_TIME
        L = math.hypot(lx, ly)
        if L > config.LOOKAHEAD_MAX:
            lx, ly = lx / L * config.LOOKAHEAD_MAX, ly / L * config.LOOKAHEAD_MAX
        tx, ty = car.x + lx, car.y + ly

        # 부드럽게 따라가기 (FPS가 달라도 같은 느낌이 나도록 exp 사용)
        k = 1.0 - math.exp(-config.CAMERA_SMOOTH * dt)
        self.x += (tx - self.x) * k
        self.y += (ty - self.y) * k

    def top_left(self):
        """화면 왼쪽 위의 월드 좌표 (맵 밖으로 안 나가게 제한)"""
        sw, sh = config.SCREEN_W, config.SCREEN_H
        x0 = int(min(max(self.x - sw / 2, 0), self.world_w - sw))
        y0 = int(min(max(self.y - sh / 2, 0), self.world_h - sh))
        return x0, y0
