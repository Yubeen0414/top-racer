"""고스트: 최고 랩을 달렸던 경로를 녹화하고 반투명 차로 다시 보여줘요.

녹화: 물리 스텝(1/60초)마다 불리고, 그중 4번에 1번(1초에 GHOST_HZ번) 위치를 저장해요.
     물리가 고정 간격이라 k번째 기록 = 랩 시작 후 정확히 k/GHOST_HZ초 지점이에요.
재생: 지금 랩 시간에 해당하는 두 기록 사이를 이어서(보간) 부드럽게 움직여요.
"""
import math

import config
from car import ghost_sprites, sprite_index

STEP_EVERY = config.PHYSICS_HZ // config.GHOST_HZ   # 몇 스텝마다 기록할지 (60/15 = 4)


class GhostRecorder:
    def __init__(self):
        self.frames = []
        self.n = 0

    def step(self, car):
        if self.n % STEP_EVERY == 0:
            self.frames.append((round(car.x, 1), round(car.y, 1), round(car.heading, 3)))
        self.n += 1

    def finish_lap(self):
        """이번 랩 기록을 돌려주고 새 랩 녹화를 준비해요."""
        frames, self.frames, self.n = self.frames, [], 0
        return frames


def _lerp_angle(a, b, t):
    # 359도 -> 1도 처럼 0을 넘어갈 때 반대로 한 바퀴 돌지 않게, 짧은 쪽으로
    d = (b - a + math.pi) % (2 * math.pi) - math.pi
    return a + d * t


class GhostPlayer:
    def __init__(self, frames):
        self.frames = frames

    def pose(self, t):
        """랩 시작 후 t초의 (x, y, 방향). 기록이 끝났으면 None (고스트가 이미 결승선 통과)."""
        f = t * config.GHOST_HZ
        i = int(f)
        if i < 0 or i + 1 >= len(self.frames):
            return None
        (x0, y0, h0), (x1, y1, h1) = self.frames[i], self.frames[i + 1]
        if math.hypot(x1 - x0, y1 - y0) > config.GHOST_SNAP_DIST:   # 복귀 버튼으로 순간이동한 구간
            return x0, y0, h0
        k = f - i
        return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, _lerp_angle(h0, h1, k)

    def draw(self, frame, t, cam_x, cam_y):
        p = self.pose(t)
        if p is None:
            return
        x, y, h = p
        spr = ghost_sprites()[sprite_index(h)]
        sx, sy = int(x - cam_x - spr.width / 2), int(y - cam_y - spr.height / 2)
        if -spr.width < sx < frame.width and -spr.height < sy < frame.height:   # 화면 안일 때만
            frame.paste(spr, (sx, sy), spr)
