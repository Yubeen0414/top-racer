"""트랙: 보이는 그림(image)과 판정용 마스크(mask)를 같이 만들어요.

지금은 코드로 트랙을 그려요. 나중에 그림판으로 그린 PNG로 바꿔도
mask 값만 같은 규칙(0=벽, 1=잔디, 2=도로)이면 나머지 코드는 그대로예요.

트랙 모양 같은 값은 tracks.py에 있고, 여기서는 그걸 받아서 그림을 만들어요.
랩/역주행 판정에 쓰는 '중심선 위 가장 가까운 점' 계산도 여기서 해요.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

import config

WALL, GRASS, ROAD = 0, 1, 2


def catmull_rom(points, samples=12):
    """기준점들을 지나는 부드러운 닫힌 곡선의 점 목록."""
    out = []
    n = len(points)
    for i in range(n):
        p0, p1, p2, p3 = points[(i - 1) % n], points[i], points[(i + 1) % n], points[(i + 2) % n]
        for s in range(samples):
            t = s / samples
            t2, t3 = t * t, t * t * t
            pt = []
            for k in range(2):
                pt.append(0.5 * (2 * p1[k]
                                 + (-p0[k] + p2[k]) * t
                                 + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                                 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3))
            out.append(tuple(pt))
    return out


class Track:
    def __init__(self, data):
        self.name = data["name"]
        self.laps = data["laps"]
        self.w, self.h = config.WORLD_W, config.WORLD_H

        self.centerline = catmull_rom(data["points"])
        self.loop = self.centerline + [self.centerline[0]]
        n = len(self.centerline)

        # 중심선 점 배열과 각 점에서의 진행 방향(단위 벡터)
        self.cl = np.array(self.centerline, dtype=np.float64)
        d = np.roll(self.cl, -1, axis=0) - self.cl
        self.tangent = d / np.linalg.norm(d, axis=1, keepdims=True)

        # 체크포인트: 중심선 점 번호로 저장. 0번은 출발선.
        k = data["checkpoints"]
        self.checkpoints = [round(i * n / k) % n for i in range(k)]

        self.image = self._draw_image(data.get("seed", 1), data.get("grass_color", (62, 140, 62)))
        self.mask = self._draw_mask()

        # 출발 위치: 출발선 바로 뒤, 트랙 진행 방향을 보고
        (px, py), (tx, ty) = self.cl[0], self.tangent[0]
        self.start_heading = math.atan2(ty, tx)
        self.start_pos = (px - tx * config.START_BACK, py - ty * config.START_BACK)

    # ---------- 판정 ----------
    def surface_at(self, x, y):
        ix, iy = int(x), int(y)
        if ix < 0 or iy < 0 or ix >= self.w or iy >= self.h:
            return WALL
        return self.mask[iy, ix]

    def nearest_index(self, x, y):
        """(x, y)에서 가장 가까운 중심선 점의 번호."""
        d = (self.cl[:, 0] - x) ** 2 + (self.cl[:, 1] - y) ** 2
        return int(np.argmin(d))

    def pose_at(self, idx):
        """중심선 idx번 점의 위치와 진행 방향 (복귀 지점으로 써요)."""
        (x, y), (tx, ty) = self.cl[idx], self.tangent[idx]
        return float(x), float(y), math.atan2(ty, tx)

    # ---------- 그리기 ----------
    def _wall_rects(self):
        t, w, h = config.WALL_THICKNESS, self.w - 1, self.h - 1
        return [(0, 0, w, t), (0, h - t, w, h), (0, 0, t, h), (w - t, 0, w, h)]

    def _cross_line(self, idx, half):
        """idx번 점에서 도로를 가로지르는 선의 양 끝."""
        (x, y), (tx, ty) = self.cl[idx], self.tangent[idx]
        nx, ny = -ty, tx
        return (x - nx * half, y - ny * half), (x + nx * half, y + ny * half)

    def _draw_image(self, seed, grass_color):
        rng = np.random.default_rng(seed)

        # 잔디: 3x3 픽셀 덩어리로 얼룩을 줘서 달릴 때 속도감이 느껴지게
        noise = rng.integers(-14, 15, (self.h // 3, self.w // 3, 1))
        grass = np.clip(np.array(grass_color) + noise, 0, 255).astype(np.uint8)
        grass = grass.repeat(3, axis=0).repeat(3, axis=1)
        img = Image.fromarray(grass, "RGB")
        d = ImageDraw.Draw(img)
        r, g, b = grass_color
        dark = (max(0, r - 22), max(0, g - 35), max(0, b - 22))   # 진한 잔디 점
        for _ in range(400):
            x, y = rng.integers(0, self.w), rng.integers(0, self.h)
            d.rectangle((x, y, x + 2, y + 2), fill=dark)

        rw, cw = config.ROAD_WIDTH, config.CURB_WIDTH
        loop = self.loop

        # 연석 (흰 바탕 위에 빨강 구간을 번갈아)
        d.line(loop, fill=(235, 235, 235), width=rw + 2 * cw, joint="curve")
        for i in range(0, len(loop) - 1, 2):
            d.line([loop[i], loop[i + 1]], fill=(210, 40, 40), width=rw + 2 * cw)

        # 도로 + 가운데 점선
        d.line(loop, fill=(70, 70, 78), width=rw, joint="curve")
        for i in range(0, len(loop) - 1, 2):
            d.line([loop[i], loop[i + 1]], fill=(190, 190, 190), width=2)

        # 출발선 (흑백 체크)
        a, b = self._cross_line(0, rw / 2)
        steps = 8
        for k in range(steps):
            t0, t1 = k / steps, (k + 1) / steps
            p = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
            q = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
            d.line([p, q], fill=(255, 255, 255) if k % 2 == 0 else (20, 20, 20), width=6)

        # 개발용: 체크포인트 위치 표시
        if config.DEBUG_CHECKPOINTS:
            for i, idx in enumerate(self.checkpoints[1:], start=1):
                d.line(self._cross_line(idx, rw / 2), fill=(255, 230, 0), width=2)
                d.text(self.centerline[idx], str(i), fill=(255, 230, 0))

        # 가장자리 벽 + 아래쪽 그림자 (가짜 깊이)
        for r in self._wall_rects():
            d.rectangle(r, fill=(125, 125, 135))
        t = config.WALL_THICKNESS
        d.rectangle((t, t + 1, self.w - 1 - t, t + 4), fill=(35, 80, 35))

        return img

    def _draw_mask(self):
        m = Image.new("L", (self.w, self.h), GRASS)
        d = ImageDraw.Draw(m)
        width = config.ROAD_WIDTH + 2 * config.CURB_WIDTH
        d.line(self.loop, fill=ROAD, width=width, joint="curve")
        for i in range(0, len(self.loop) - 1, 2):
            d.line([self.loop[i], self.loop[i + 1]], fill=ROAD, width=width)
        for r in self._wall_rects():
            d.rectangle(r, fill=WALL)
        return np.array(m)
