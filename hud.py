"""레이스 화면 위에 겹쳐 그리는 정보.

  왼쪽 위    LAP 2/3, 이번 랩 시간
  가운데 위   구간 기록 차이 (-0.42 초록 / +0.31 빨강)
  오른쪽 위   전체 시간, 저장된 최고 랩
  왼쪽 아래   속도
  가운데 아래  부스트 게이지 (3칸)
  오른쪽 아래  미니맵, FPS (개발용, config.SHOW_FPS)
  가운데     카운트다운, GO!, 랩 알림, WRONG WAY, FINISH!
"""
from PIL import ImageDraw

import config
import ui

WHITE = (255, 255, 255)
GREEN = (120, 255, 140)
YELLOW = (255, 220, 0)
RED = (255, 60, 50)
CYAN = (60, 210, 255)
ORANGE = (255, 140, 0)
CX, CY = config.SCREEN_W // 2, config.SCREEN_H // 2


def draw_race(frame, session, fps, split=None):
    d = ImageDraw.Draw(frame)
    lap, car, laps = session.lap, session.car, session.track.laps
    right = config.SCREEN_W - 6

    # 왼쪽 위: 랩 + 이번 랩 시간
    ui.text(d, (6, 4), f"LAP {min(lap.lap, laps)}/{laps}", 16)
    shown = lap.lap_times[-1] if lap.finished else lap.current_lap_time   # 결승 후엔 마지막 랩 기록
    ui.text(d, (6, 24), ui.format_time(shown), 13)

    # 가운데 위: 구간 기록 차이
    if split is not None:
        ui.text(d, (CX, 6), f"{split:+.2f}", 15, GREEN if split <= 0 else RED, anchor="mt")

    # 오른쪽 위: 전체 시간 + 최고 랩 (저장된 기록)
    ui.text(d, (right, 4), ui.format_time(lap.time), 13, anchor="ra")
    best = session.best_lap
    if best is not None:
        ui.text(d, (right, 22), "BEST " + ui.format_time(best), 10, GREEN, anchor="ra", stroke=1)

    # 오른쪽 아래: 미니맵
    minimap(frame, session)

    # 왼쪽 아래: 속도
    fwd = abs(car.forward_speed())
    ui.text(d, (6, 214), f"{int(fwd * config.SPEED_TO_KMH):3d} km/h", 16)

    # 가운데 아래: 부스트 게이지 (칸마다 채워진 정도)
    color = ORANGE if car.boosting else CYAN
    for i in range(config.BOOST_SEGMENTS):
        x0 = 110 + i * 22
        d.rectangle((x0, 221, x0 + 19, 231), fill=(0, 0, 0))
        fill = min(1.0, max(0.0, car.gauge - i))
        if fill > 0:
            d.rectangle((x0 + 1, 222, x0 + 1 + int(17 * fill), 230), fill=color if fill >= 1 else (40, 110, 140))

    # 오른쪽 아래: FPS (개발용)
    if config.SHOW_FPS and fps > 0:
        ui.text(d, (right, 222), f"{fps:4.1f}", 10, YELLOW, anchor="ra", stroke=1)


def medal(d, cx, cy, r, kind):
    """메달 아이콘. kind가 None이면 빈 동그라미."""
    from progress import MEDAL_COLORS
    if kind is None:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(110, 110, 110), width=1)
        return
    c = MEDAL_COLORS[kind]
    d.polygon([(cx - r * 0.8, cy - r * 1.9), (cx - r * 0.1, cy - r * 0.6), (cx - r * 0.6, cy - r * 0.6)],
              fill=(60, 90, 200))                                                    # 리본
    d.polygon([(cx + r * 0.8, cy - r * 1.9), (cx + r * 0.1, cy - r * 0.6), (cx + r * 0.6, cy - r * 0.6)],
              fill=(200, 50, 50))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c, outline=tuple(v // 2 for v in c), width=max(1, r // 5))
    h = max(1, r // 3)
    d.ellipse((cx - r * 0.5 - h / 2, cy - r * 0.5 - h / 2, cx - r * 0.5 + h / 2, cy - r * 0.5 + h / 2),
              fill=(255, 255, 255))                                                  # 반짝임


def minimap(frame, session):
    """오른쪽 아래 미니맵: 미리 그린 트랙 모양 위에 고스트(파랑)와 내 차(빨강) 점만 찍어요."""
    mm, to_map = session.track.minimap
    ox, oy = config.SCREEN_W - mm.width - 6, 210 - mm.height
    frame.paste(mm, (ox, oy), mm)
    d = ImageDraw.Draw(frame)
    if session.ghost and not session.lap.finished:
        p = session.ghost.pose(session.lap.current_lap_time)
        if p:
            gx, gy = to_map(p[0], p[1])
            d.ellipse((ox + gx - 2, oy + gy - 2, ox + gx + 2, oy + gy + 2), fill=(90, 170, 255))
    cx, cy = to_map(session.car.x, session.car.y)
    d.ellipse((ox + cx - 3, oy + cy - 3, ox + cx + 3, oy + cy + 3), fill=(240, 50, 40), outline=WHITE)


def big_center(frame, s, color):
    """화면 가운데 큰 글자 (3, 2, 1, GO!, FINISH!)"""
    ui.text(ImageDraw.Draw(frame), (CX, CY - 20), s, 40, color, anchor="mm", stroke=4)


def banner(frame, title, sub, color=YELLOW):
    """랩 완료 알림: 큰 제목 + 작은 시간"""
    d = ImageDraw.Draw(frame)
    ui.text(d, (CX, 72), title, 20, color, anchor="mm", stroke=3)
    ui.text(d, (CX, 96), sub, 14, anchor="mm")


def wrong_way(frame):
    ui.text(ImageDraw.Draw(frame), (CX, CY + 24), "WRONG WAY", 22, RED, anchor="mm", stroke=3)
