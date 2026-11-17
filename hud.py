"""레이스 화면 위에 겹쳐 그리는 정보.

  왼쪽 위   LAP 2/3, 이번 랩 시간
  오른쪽 위  전체 시간, 이번 판 최고 랩
  왼쪽 아래  속도 숫자 + 막대
  오른쪽 아래 FPS (개발용, config.SHOW_FPS)
  가운데    카운트다운, GO!, 랩 알림, WRONG WAY, FINISH!
"""
from PIL import ImageDraw

import config
import ui

WHITE = (255, 255, 255)
GREEN = (120, 255, 140)
YELLOW = (255, 220, 0)
RED = (255, 60, 50)
CX, CY = config.SCREEN_W // 2, config.SCREEN_H // 2


def draw_race(frame, session, fps):
    d = ImageDraw.Draw(frame)
    lap, car, laps = session.lap, session.car, session.track.laps
    right = config.SCREEN_W - 6

    # 왼쪽 위: 랩 + 이번 랩 시간
    ui.text(d, (6, 4), f"LAP {min(lap.lap, laps)}/{laps}", 16)
    shown = lap.lap_times[-1] if lap.finished else lap.current_lap_time   # 결승 후엔 마지막 랩 기록
    ui.text(d, (6, 24), ui.format_time(shown), 13)

    # 오른쪽 위: 전체 시간 + 최고 랩
    ui.text(d, (right, 4), ui.format_time(lap.time), 13, anchor="ra")
    if lap.best_lap is not None:
        ui.text(d, (right, 22), "BEST " + ui.format_time(lap.best_lap), 10, GREEN, anchor="ra", stroke=1)

    # 왼쪽 아래: 속도 숫자 + 막대
    fwd = abs(car.forward_speed())
    ui.text(d, (6, 214), f"{int(fwd * config.SPEED_TO_KMH):3d} km/h", 16)
    ratio = min(1.0, fwd / config.MAX_SPEED)
    d.rectangle((110, 222, 170, 230), fill=(0, 0, 0))
    d.rectangle((111, 223, 111 + int(58 * ratio), 229),
                fill=(255, 200, 0) if not car.on_grass else (120, 200, 80))

    # 오른쪽 아래: FPS (개발용)
    if config.SHOW_FPS:
        ui.text(d, (right, 222), f"{fps:4.1f}", 10, YELLOW, anchor="ra", stroke=1)


def big_center(frame, s, color):
    """화면 가운데 큰 글자 (3, 2, 1, GO!, FINISH!)"""
    ui.text(ImageDraw.Draw(frame), (CX, CY - 20), s, 40, color, anchor="mm", stroke=4)


def banner(frame, title, sub):
    """랩 완료 알림: 큰 제목 + 작은 시간"""
    d = ImageDraw.Draw(frame)
    ui.text(d, (CX, 72), title, 20, YELLOW, anchor="mm", stroke=3)
    ui.text(d, (CX, 96), sub, 14, anchor="mm")


def wrong_way(frame):
    ui.text(ImageDraw.Draw(frame), (CX, CY + 24), "WRONG WAY", 22, RED, anchor="mm", stroke=3)
