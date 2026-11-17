"""게임 화면(상태)들. main.py는 '지금 상태' 하나만 돌려요.

  TitleState -> CountdownState -> RaceState -> ResultState -> (다시 달리기 / 타이틀)

각 상태가 가진 함수:
  frame(dt, inp)  화면 한 장마다 한 번. 버튼을 '누른 순간', 카메라처럼 결과에 영향 없는 것.
  step(dt, inp)   물리 간격(1/60초)마다 한 번. 차 움직임, 시간 재기처럼 기록에 영향 주는 것.
  draw(fps)       화면에 보낼 그림을 돌려줘요.
상태를 바꾸고 싶으면 self.next 에 다음 상태를 넣으면 main.py가 바꿔줘요.
"""
from PIL import Image, ImageDraw

import config
import hud
import ui
from camera import Camera
from car import Car
from hardware import BUTTONS
from race import LapTracker


class _NoInput:
    """아무 버튼도 안 누른 입력 (카운트다운, 결승 후 차를 멈출 때)"""
    def held(self, name):
        return False

    def pressed(self, name):
        return False


NO_INPUT = _NoInput()
BLACK = (0, 0, 0)


class State:
    def __init__(self, game):
        self.game = game
        self.next = None

    def frame(self, dt, inp):
        pass

    def step(self, dt, inp):
        pass

    def draw(self, fps):
        raise NotImplementedError


class RaceSession:
    """한 판에 필요한 것들 (차, 카메라, 랩 기록)을 묶어둔 것."""

    def __init__(self, track):
        self.track = track
        self.car = Car(*track.start_pos, track.start_heading)
        self.cam = Camera(self.car.x, self.car.y, track.w, track.h)
        self.lap = LapTracker(track)
        self.lap.start(self.car)

    def render_world(self):
        x0, y0 = self.cam.top_left()
        frame = self.track.image.crop((x0, y0, x0 + config.SCREEN_W, y0 + config.SCREEN_H))
        self.car.draw(frame, x0, y0)
        return frame


def _darken(img, amount):
    return Image.blend(img, Image.new("RGB", img.size, BLACK), amount)


# ---------------------------------------------------------------- 시작 화면
class TitleState(State):
    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        # 배경은 한 번만 만들어 두고 매 프레임 복사만 해요.
        bg = game.track.image.resize((config.SCREEN_W, config.SCREEN_H), Image.BILINEAR)
        self.bg = _darken(bg, 0.55)
        d = ImageDraw.Draw(self.bg)
        ui.text(d, (hud.CX, 78), "TOP RACER", 30, anchor="mm", stroke=3)
        ui.text(d, (hud.CX, 108), "GHOST LAP", 18, (120, 200, 255), anchor="mm")
        ui.text(d, (hud.CX, 136), game.track.name, 11, (200, 200, 200), anchor="mm", stroke=1)

    def frame(self, dt, inp):
        self.t += dt
        if any(inp.pressed(b) for b in BUTTONS):
            self.next = CountdownState(self.game, RaceSession(self.game.track))

    def draw(self, fps):
        img = self.bg.copy()
        if int(self.t * 2) % 2 == 0:   # 0.5초마다 깜빡
            ui.text(ImageDraw.Draw(img), (hud.CX, 186), "PRESS ANY BUTTON", 12, anchor="mm")
        return img


# ---------------------------------------------------------------- 카운트다운
class CountdownState(State):
    def __init__(self, game, session):
        super().__init__(game)
        self.s = session
        self.t = 0.0

    def frame(self, dt, inp):
        self.s.cam.update(dt, self.s.car)

    def step(self, dt, inp):
        self.t += dt
        if self.t >= config.COUNTDOWN_SEC:
            self.next = RaceState(self.game, self.s)

    def draw(self, fps):
        frame = self.s.render_world()
        hud.draw_race(frame, self.s, fps)
        n = max(1, config.COUNTDOWN_SEC - int(self.t))
        hud.big_center(frame, str(n), hud.YELLOW)
        return frame


# ---------------------------------------------------------------- 레이스
class RaceState(State):
    def __init__(self, game, session):
        super().__init__(game)
        self.s = session
        self.banner = None        # (제목, 시간 글자, 남은 시간)
        self.finish_t = 0.0

    def frame(self, dt, inp):
        s = self.s
        s.cam.update(dt, s.car)
        # 가운데 버튼: 마지막 체크포인트로 복귀 (시간은 계속 흘러요)
        if inp.pressed("center") and not s.lap.finished:
            s.car.reset(*s.lap.respawn_pose())
            s.lap.respawned(s.car)

    def step(self, dt, inp):
        s = self.s
        s.car.update(dt, NO_INPUT if s.lap.finished else inp, s.track)
        event = s.lap.step(dt, s.car)

        if event == "lap":
            title = "FINAL LAP" if s.lap.lap == s.track.laps else f"LAP {s.lap.lap}"
            self.banner = [title, ui.format_time(s.lap.lap_times[-1]), config.LAP_BANNER_SEC]
        elif self.banner:
            self.banner[2] -= dt
            if self.banner[2] <= 0:
                self.banner = None

        if s.lap.finished:
            self.finish_t += dt
            if self.finish_t >= config.FINISH_SHOW_SEC:
                self.next = ResultState(self.game, s)

    def draw(self, fps):
        s = self.s
        frame = s.render_world()
        hud.draw_race(frame, s, fps)
        if s.lap.finished:
            hud.big_center(frame, "FINISH!", hud.YELLOW)
        elif s.lap.time < config.GO_SHOW_SEC:
            hud.big_center(frame, "GO!", hud.GREEN)
        elif self.banner:
            hud.banner(frame, self.banner[0], self.banner[1])
        if s.lap.wrong_way and int(s.lap.time * 3) % 2 == 0:
            hud.wrong_way(frame)
        return frame


# ---------------------------------------------------------------- 결과 화면
class ResultState(State):
    def __init__(self, game, session):
        super().__init__(game)
        self.t = 0.0
        self.img = self._make(session)

    @staticmethod
    def _make(s):
        img = _darken(s.render_world(), 0.65)
        d = ImageDraw.Draw(img)
        cx = hud.CX
        laps = s.lap.lap_times
        ui.text(d, (cx, 26), "RESULT", 22, anchor="mm", stroke=3)
        ui.text(d, (cx, 56), "TOTAL", 11, (190, 190, 190), anchor="mm", stroke=1)
        ui.text(d, (cx, 78), ui.format_time(sum(laps)), 24, hud.YELLOW, anchor="mm", stroke=3)

        best = laps.index(min(laps))
        y = 112
        for i, t in enumerate(laps):
            color = hud.GREEN if i == best else hud.WHITE
            ui.text(d, (50, y), f"LAP {i + 1}", 14, color, anchor="lm")
            ui.text(d, (168, y), ui.format_time(t), 14, color, anchor="rm")
            if i == best:
                ui.text(d, (174, y), "BEST", 10, color, anchor="lm", stroke=1)
            y += 22

        ui.text(d, (cx, 214), "A: RETRY     B: TITLE", 12, anchor="mm")
        return img

    def frame(self, dt, inp):
        self.t += dt
        if self.t < config.RESULT_INPUT_DELAY:
            return
        if inp.pressed("a"):
            self.next = CountdownState(self.game, RaceSession(self.game.track))
        elif inp.pressed("b"):
            self.next = TitleState(self.game)

    def draw(self, fps):
        return self.img.copy()
