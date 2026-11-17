"""트랙: 보이는 그림(image)과 판정용 마스크(mask)를 같이 만들어요.

트랙 모양·색·장식 값은 tracks.py에 있고, 여기서는 그걸 받아서 그림과 마스크를 만들어요.
mask 규칙: 0=벽, 1=잔디, 2=도로, 3=모래
나중에 그림판으로 그린 PNG로 바꿔도 mask 값만 같은 규칙이면 나머지 코드는 그대로예요.

장식 (tracks.py에서 켜고 끔)
  sand       급한 코너 바깥쪽에 모래 (밟으면 크게 느려짐)
  sea        맵 한쪽이 바다 (벽) + 모래사장
  buildings  도로 밖에 건물 (벽). 도로와 충분히 떨어진 곳에만 놓아요.
  lamps      도로 옆 가로등 (보기만)

랩/역주행 판정에 쓰는 '중심선 위 가장 가까운 점' 계산도 여기서 해요.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

import config

WALL, GRASS, ROAD, SAND = 0, 1, 2, 3

DEFAULT_THEME = {
    "grass": (62, 140, 62),          # 바깥 땅
    "grass_dot": (40, 105, 40),      # 땅 얼룩
    "road": (70, 70, 78),
    "line": (190, 190, 190),         # 가운데 점선
    "curb_a": (235, 235, 235),
    "curb_b": (210, 40, 40),
    "sand": (222, 196, 130),
    "wall": (125, 125, 135),
    "map_bg": (20, 40, 20),          # 미니맵 배경
}


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
        self.data = data
        self.name = data["name"]
        self.laps = data["laps"]
        self.medals = data.get("medals")
        self.w, self.h = data.get("size", (config.WORLD_W, config.WORLD_H))
        self.road_w = data.get("road_width", config.ROAD_WIDTH)
        self.theme = dict(DEFAULT_THEME, **data.get("theme", {}))
        self.rng = np.random.default_rng(data.get("seed", 1))

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

        # 마스크와 그림을 같은 도형으로 같이 그려요 (보이는 것 = 판정)
        self.image, self.mask = self._build()

        # 출발 위치: 출발선 바로 뒤, 트랙 진행 방향을 보고
        (px, py), (tx, ty) = self.cl[0], self.tangent[0]
        self.start_heading = math.atan2(ty, tx)
        self.start_pos = (px - tx * config.START_BACK, py - ty * config.START_BACK)

    @property
    def key(self):
        """기록 비교용 지문 (save.py 참고)"""
        if not hasattr(self, "_key"):
            import save
            self._key = save.fingerprint(self.data)
        return self._key

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

    def dist_to_center(self, x, y):
        return float(np.sqrt(((self.cl[:, 0] - x) ** 2 + (self.cl[:, 1] - y) ** 2).min()))

    def pose_at(self, idx):
        """중심선 idx번 점의 위치와 진행 방향 (복귀 지점으로 써요)."""
        (x, y), (tx, ty) = self.cl[idx], self.tangent[idx]
        return float(x), float(y), math.atan2(ty, tx)

    # ---------- 만들기 ----------
    def _wall_rects(self):
        t, w, h = config.WALL_THICKNESS, self.w - 1, self.h - 1
        return [(0, 0, w, t), (0, h - t, w, h), (0, 0, t, h), (w - t, 0, w, h)]

    def _cross_line(self, idx, half):
        """idx번 점에서 도로를 가로지르는 선의 양 끝."""
        (x, y), (tx, ty) = self.cl[idx], self.tangent[idx]
        nx, ny = -ty, tx
        return (x - nx * half, y - ny * half), (x + nx * half, y + ny * half)

    def _build(self):
        th, rng = self.theme, self.rng
        rw, cw = self.road_w, config.CURB_WIDTH
        outer = rw + 2 * cw

        # 바탕 땅: 3x3 픽셀 덩어리로 얼룩을 줘서 달릴 때 속도감이 느껴지게
        noise = rng.integers(-14, 15, (self.h // 3 + 1, self.w // 3 + 1, 1))
        base = np.clip(np.array(th["grass"]) + noise, 0, 255).astype(np.uint8)
        base = base.repeat(3, axis=0).repeat(3, axis=1)[: self.h, : self.w]
        img = Image.fromarray(base, "RGB")
        mask = Image.new("L", (self.w, self.h), GRASS)
        d, m = ImageDraw.Draw(img), ImageDraw.Draw(mask)
        for _ in range(self.w * self.h // 2300):
            x, y = rng.integers(0, self.w), rng.integers(0, self.h)
            d.rectangle((x, y, x + 2, y + 2), fill=th["grass_dot"])

        if "sea" in self.data:
            self._draw_sea(d, m, self.data["sea"])
        if self.data.get("sand"):
            self._draw_corner_sand(d, m)
        if self.data.get("buildings"):
            self._draw_buildings(d, m, self.data["buildings"])

        # 연석 (흰 바탕 위에 색 구간을 번갈아) + 판정상으로는 도로
        loop = self.loop
        d.line(loop, fill=th["curb_a"], width=outer, joint="curve")
        for i in range(0, len(loop) - 1, 2):
            d.line([loop[i], loop[i + 1]], fill=th["curb_b"], width=outer)
        m.line(loop, fill=ROAD, width=outer, joint="curve")
        for i in range(0, len(loop) - 1, 2):
            m.line([loop[i], loop[i + 1]], fill=ROAD, width=outer)

        # 도로 + 가운데 점선
        d.line(loop, fill=th["road"], width=rw, joint="curve")
        for i in range(0, len(loop) - 1, 2):
            d.line([loop[i], loop[i + 1]], fill=th["line"], width=2)

        # 출발선 (흑백 체크)
        a, b = self._cross_line(0, rw / 2)
        steps = 8
        for k in range(steps):
            t0, t1 = k / steps, (k + 1) / steps
            p = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
            q = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
            d.line([p, q], fill=(255, 255, 255) if k % 2 == 0 else (20, 20, 20), width=6)

        if self.data.get("lamps"):
            self._draw_lamps(d)

        # 개발용: 체크포인트 위치 표시
        if config.DEBUG_CHECKPOINTS:
            for i, idx in enumerate(self.checkpoints[1:], start=1):
                d.line(self._cross_line(idx, rw / 2), fill=(255, 230, 0), width=2)
                d.text(self.centerline[idx], str(i), fill=(255, 230, 0))

        # 가장자리 벽 + 아래쪽 그림자 (가짜 깊이)
        for r in self._wall_rects():
            d.rectangle(r, fill=th["wall"])
            m.rectangle(r, fill=WALL)
        t = config.WALL_THICKNESS
        d.rectangle((t, t + 1, self.w - 1 - t, t + 4), fill=tuple(c // 2 for c in th["grass"]))

        return img, np.array(mask)

    def _draw_corner_sand(self, d, m):
        """급한 코너 바깥쪽에 모래. 바깥 = 도는 방향의 반대쪽."""
        n = len(self.centerline)
        hw = self.road_w / 2 + config.CURB_WIDTH
        for i in range(n):
            t0, t1 = self.tangent[(i - 2) % n], self.tangent[(i + 2) % n]
            turn = math.atan2(t0[0] * t1[1] - t0[1] * t1[0], float(t0 @ t1))   # +면 오른쪽으로 도는 중
            if abs(turn) < config.SAND_CORNER_TURN:
                continue
            tx, ty = self.tangent[i]
            rx, ry = -ty, tx                       # 오른쪽 방향
            side = -1 if turn > 0 else 1           # 바깥쪽
            r = 22 + int(self.rng.integers(0, 10))
            cx = self.cl[i][0] + rx * side * (hw + r * 0.7)
            cy = self.cl[i][1] + ry * side * (hw + r * 0.7)
            box = (cx - r, cy - r, cx + r, cy + r)
            d.ellipse(box, fill=self.theme["sand"])
            m.ellipse(box, fill=SAND)
            for _ in range(6):   # 모래 알갱이 점
                px, py = cx + self.rng.uniform(-r, r) * 0.7, cy + self.rng.uniform(-r, r) * 0.7
                d.point((px, py), fill=tuple(max(0, c - 40) for c in self.theme["sand"]))

    def _draw_sea(self, d, m, sea):
        """맵 한쪽 바다(벽) + 그 앞 모래사장(모래). sea = {"side": "bottom", "depth": 120}"""
        depth, beach = sea["depth"], sea.get("beach", 36)
        w, h = self.w, self.h
        if sea["side"] == "bottom":
            water, sand = (0, h - depth, w, h), (0, h - depth - beach, w, h - depth)
        elif sea["side"] == "right":
            water, sand = (w - depth, 0, w, h), (w - depth - beach, 0, w - depth, h)
        else:
            raise ValueError("sea side: bottom/right")
        d.rectangle(sand, fill=self.theme["sand"])
        m.rectangle(sand, fill=SAND)
        d.rectangle(water, fill=sea.get("color", (40, 110, 170)))
        m.rectangle(water, fill=WALL)
        # 물결 무늬
        x0, y0, x1, y1 = water
        for _ in range((x1 - x0) * (y1 - y0) // 900):
            x, y = self.rng.integers(x0, x1), self.rng.integers(y0, y1)
            d.line((x, y, x + 8, y), fill=(120, 180, 220))

    def _draw_buildings(self, d, m, count):
        """도로에서 충분히 떨어진 곳에 건물(벽)을 놓아요. 위에서 본 지붕 + 불 켜진 창문."""
        clear = self.road_w / 2 + config.CURB_WIDTH + 18
        boxes = []
        placed, tries = 0, 0
        while placed < count and tries < count * 40:
            tries += 1
            bw, bh = int(self.rng.integers(50, 120)), int(self.rng.integers(50, 120))
            x0 = int(self.rng.integers(config.WALL_THICKNESS, self.w - bw - config.WALL_THICKNESS))
            y0 = int(self.rng.integers(config.WALL_THICKNESS, self.h - bh - config.WALL_THICKNESS))
            # 건물 가장자리 점들이 모두 중심선에서 충분히 멀어야 해요
            pts = [(x0 + bw * a / 4, y0 + bh * b / 4) for a in range(5) for b in range(5)]
            if min(self.dist_to_center(x, y) for x, y in pts) < clear:
                continue
            box = (x0, y0, x0 + bw, y0 + bh)
            gap = 10   # 건물끼리 겹치지 않게
            if any(x0 < b[2] + gap and b[0] < box[2] + gap and y0 < b[3] + gap and b[1] < box[3] + gap
                   for b in boxes):
                continue
            boxes.append(box)
            m.rectangle(box, fill=WALL)
            d.rectangle((x0 + 4, y0 + 5, x0 + bw + 4, y0 + bh + 5), fill=(8, 10, 16))   # 그림자
            d.rectangle(box, fill=self.theme["building"], outline=self.theme["building_edge"], width=2)
            for _ in range(bw * bh // 300):   # 창문 불빛
                wx = x0 + 6 + int(self.rng.integers(0, max(1, bw - 12)))
                wy = y0 + 6 + int(self.rng.integers(0, max(1, bh - 12)))
                d.rectangle((wx, wy, wx + 2, wy + 2), fill=(250, 220, 120))
            placed += 1

    def _draw_lamps(self, d):
        """도로 양옆 가로등 (보기만, 판정 없음)"""
        n = len(self.centerline)
        off = self.road_w / 2 + config.CURB_WIDTH + 7
        for i in range(0, n, 5):
            (x, y), (tx, ty) = self.cl[i], self.tangent[i]
            side = 1 if (i // 5) % 2 == 0 else -1
            lx, ly = x - ty * off * side, y + tx * off * side
            d.ellipse((lx - 9, ly - 9, lx + 9, ly + 9), fill=(70, 66, 40))     # 바닥에 비친 빛
            d.ellipse((lx - 3, ly - 3, lx + 3, ly + 3), fill=(255, 235, 150))

    # ---------- 미니맵 ----------
    def make_minimap(self, size):
        """트랙 모양만 작게 (시작할 때 한 번). 반환: (RGBA 그림, 월드->미니맵 변환 함수)"""
        pad = 4
        s = (size - 2 * pad) / max(self.w, self.h)
        ox = pad + (size - 2 * pad - self.w * s) / 2
        oy = pad + (size - 2 * pad - self.h * s) / 2

        def to_map(x, y):
            return ox + x * s, oy + y * s

        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((0, 0, size - 1, size - 1), radius=6, fill=self.theme["map_bg"] + (170,))
        pts = [to_map(x, y) for x, y in self.loop]
        d.line(pts, fill=(235, 235, 235, 255), width=3, joint="curve")
        a, b = self._cross_line(0, self.road_w)
        d.line([to_map(*a), to_map(*b)], fill=(255, 220, 0, 255), width=2)   # 출발선
        return img, to_map
