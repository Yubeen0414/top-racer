"""게임 화면(상태)들. main.py는 '지금 상태' 하나만 돌려요.

  TitleState -> CountdownState -> RaceState <-> PauseState
                                     -> ResultState -> (다시 달리기 / 타이틀)

각 상태가 가진 함수:
  frame(dt, inp)  화면 한 장마다 한 번. 메뉴 버튼, 카메라처럼 기록에 영향 없는 것.
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
from ghost import GhostPlayer, GhostRecorder
from hardware import BUTTONS
from race import LapTracker


class _NoInput:
    """아무 버튼도 안 누른 입력 (결승 후 차를 멈출 때)"""
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
    """한 판에 필요한 것들 (차, 카메라, 랩 기록, 고스트)을 묶어둔 것."""

    def __init__(self, game):
        self.game = game
        self.track = track = game.track
        self.car = Car(*track.start_pos, track.start_heading)
        self.cam = Camera(self.car.x, self.car.y, track.w, track.h)
        self.lap = LapTracker(track)
        self.lap.start(self.car)

        self.record = game.save.record(track)        # 저장된 기록 (없으면 None)
        ghost = self.record.get("ghost") if self.record else None
        self.ghost = GhostPlayer(ghost) if ghost else None
        self.recorder = GhostRecorder()
        self.recorder.step(self.car)                 # 랩 시간 0초 위치
        self.new_record = False                      # 이번 판에 최고 총 기록을 깼는지

    @property
    def best_lap(self):
        return self.record.get("best_lap") if self.record else None

    def split_delta(self, idx, t):
        """idx번째 체크포인트를 t초에 지났을 때 최고 랩과의 차이 (비교할 기록 없으면 None)"""
        ref = self.record.get("splits", []) if self.record else []
        return t - ref[idx] if idx < len(ref) else None

    def lap_completed(self, finished):
        """랩이 끝난 순간 호출. 최고 랩이면 고스트와 함께 저장. 최고 랩과의 차이를 돌려줘요."""
        t = self.lap.lap_times[-1]
        frames = self.recorder.finish_lap()
        best = self.best_lap
        delta = t - best if best is not None else None
        save = self.game.save
        if best is None or t < best:
            self.record = save.update(self.track, best_lap=t, splits=self.lap.last_lap_splits, ghost=frames)
            self.ghost = GhostPlayer(frames)          # 다음 랩부터 새 고스트와 경쟁
        if finished:
            total = self.lap.time
            old = self.record.get("best_total")
            if old is None or total < old:
                self.record = save.update(self.track, best_total=total)
                self.new_record = True
        return delta

    def render_world(self):
        x0, y0 = self.cam.top_left()
        frame = self.track.image.crop((x0, y0, x0 + config.SCREEN_W, y0 + config.SCREEN_H))
        if self.ghost and not self.lap.finished:
            self.ghost.draw(frame, self.lap.current_lap_time, x0, y0)
        self.car.draw(frame, x0, y0, flicker=int(self.lap.time * 20))
        return frame


def _darken(img, amount):
    return Image.blend(img, Image.new("RGB", img.size, BLACK), amount)


# ---------------------------------------------------------------- 시작 화면
class TitleState(State):
    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        track = game.track
        # 배경은 한 번만 만들어 두고 매 프레임 복사만 해요.
        bg = track.image.resize((config.SCREEN_W, config.SCREEN_H), Image.BILINEAR)
        self.bg = _darken(bg, 0.55)
        d = ImageDraw.Draw(self.bg)
        ui.text(d, (hud.CX, 74), "TOP RACER", 30, anchor="mm", stroke=3)
        ui.text(d, (hud.CX, 104), "GHOST LAP", 18, (120, 200, 255), anchor="mm")
        ui.text(d, (hud.CX, 132), track.name, 11, (200, 200, 200), anchor="mm", stroke=1)
        rec = game.save.record(track)
        if rec and rec.get("best_total") is not None:
            ui.text(d, (hud.CX, 150), "RECORD " + ui.format_time(rec["best_total"]), 11, hud.GREEN,
                    anchor="mm", stroke=1)

    def frame(self, dt, inp):
        self.t += dt
        if any(inp.pressed(b) for b in BUTTONS):
            self.next = CountdownState(self.game, RaceSession(self.game))

    def draw(self, fps):
        img = self.bg.copy()
        if int(self.t * 2) % 2 == 0:   # 0.5초마다 깜빡
            ui.text(ImageDraw.Draw(img), (hud.CX, 190), "PRESS ANY BUTTON", 12, anchor="mm")
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
        self.banner = None        # [제목, 시간 글자, 색, 남은 시간]
        self.split = None         # [차이(초), 남은 시간]
        self.finish_t = 0.0

    def frame(self, dt, inp):
        s = self.s
        s.cam.update(dt, s.car)
        if inp.pressed("center") and not s.lap.finished:
            self.next = PauseState(self.game, self)

    def respawn(self):
        """마지막 체크포인트로 복귀 (시간은 계속 흘러요)"""
        s = self.s
        s.car.reset(*s.lap.respawn_pose())
        s.lap.respawned(s.car)

    def step(self, dt, inp):
        s = self.s
        s.car.update(dt, NO_INPUT if s.lap.finished else inp, s.track)
        event = s.lap.step(dt, s.car)

        if event == "cp":
            delta = s.split_delta(len(s.lap.splits) - 1, s.lap.splits[-1])
            if delta is not None:
                self.split = [delta, config.SPLIT_SHOW_SEC]
        elif event in ("lap", "finish"):
            delta = s.lap_completed(finished=(event == "finish"))   # 최고 랩과의 차이
            if delta is not None:
                self.split = [delta, config.SPLIT_SHOW_SEC]
            if event == "lap":
                title = "FINAL LAP" if s.lap.lap == s.track.laps else f"LAP {s.lap.lap}"
                sub = ui.format_time(s.lap.lap_times[-1])
                if delta is not None and delta < 0:
                    sub += "  BEST!"
                self.banner = [title, sub, config.LAP_BANNER_SEC]

        if not s.lap.finished:
            s.recorder.step(s.car)

        for timer in (self.banner, self.split):
            if timer is not None:
                timer[-1] -= dt
        if self.banner and self.banner[-1] <= 0:
            self.banner = None
        if self.split and self.split[-1] <= 0:
            self.split = None

        if s.lap.finished:
            self.finish_t += dt
            if self.finish_t >= config.FINISH_SHOW_SEC:
                self.next = ResultState(self.game, s)

    def draw(self, fps):
        s = self.s
        frame = s.render_world()
        hud.draw_race(frame, s, fps, split=self.split[0] if self.split else None)
        if s.lap.finished:
            hud.big_center(frame, "FINISH!", hud.YELLOW)
        elif s.lap.time < config.GO_SHOW_SEC:
            hud.big_center(frame, "GO!", hud.GREEN)
        elif self.banner:
            hud.banner(frame, self.banner[0], self.banner[1])
        if s.lap.wrong_way and int(s.lap.time * 3) % 2 == 0:
            hud.wrong_way(frame)
        return frame


# ---------------------------------------------------------------- 일시정지
class PauseState(State):
    ITEMS = ("CONTINUE", "RESPAWN", "RESTART", "TITLE")

    def __init__(self, game, race):
        super().__init__(game)
        self.race = race
        self.sel = 0
        self.bg = _darken(race.draw(0.0), 0.6)    # 멈춘 화면을 어둡게 해서 배경으로

    def _resume(self):
        self.race.next = None
        self.next = self.race

    def frame(self, dt, inp):
        if inp.pressed("up"):
            self.sel = (self.sel - 1) % len(self.ITEMS)
        elif inp.pressed("down"):
            self.sel = (self.sel + 1) % len(self.ITEMS)
        elif inp.pressed("center") or inp.pressed("b"):
            self._resume()
        elif inp.pressed("a"):
            item = self.ITEMS[self.sel]
            if item == "CONTINUE":
                self._resume()
            elif item == "RESPAWN":
                self.race.respawn()
                self._resume()
            elif item == "RESTART":
                self.next = CountdownState(self.game, RaceSession(self.game))
            else:
                self.next = TitleState(self.game)

    def draw(self, fps):
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        ui.text(d, (hud.CX, 52), "PAUSE", 24, anchor="mm", stroke=3)
        for i, item in enumerate(self.ITEMS):
            y = 96 + i * 26
            if i == self.sel:
                d.rectangle((50, y - 11, 190, y + 11), fill=(40, 90, 160))
            ui.text(d, (hud.CX, y), item, 15, hud.WHITE if i == self.sel else (170, 170, 170), anchor="mm")
        ui.text(d, (hud.CX, 214), "A: SELECT   B: BACK", 11, (200, 200, 200), anchor="mm", stroke=1)
        return img


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
        ui.text(d, (cx, 24), "RESULT", 22, anchor="mm", stroke=3)
        ui.text(d, (cx, 50), "TOTAL", 11, (190, 190, 190), anchor="mm", stroke=1)
        ui.text(d, (cx, 72), ui.format_time(s.lap.time), 24, hud.YELLOW, anchor="mm", stroke=3)
        if s.new_record:
            ui.text(d, (cx, 98), "NEW RECORD!", 15, hud.GREEN, anchor="mm", stroke=2)
        elif s.record and s.record.get("best_total") is not None:
            ui.text(d, (cx, 98), "RECORD " + ui.format_time(s.record["best_total"]), 12,
                    (190, 190, 190), anchor="mm", stroke=1)

        best = laps.index(min(laps))
        y = 126
        for i, t in enumerate(laps):
            color = hud.GREEN if i == best else hud.WHITE
            ui.text(d, (50, y), f"LAP {i + 1}", 14, color, anchor="lm")
            ui.text(d, (168, y), ui.format_time(t), 14, color, anchor="rm")
            if i == best:
                ui.text(d, (174, y), "BEST", 10, color, anchor="lm", stroke=1)
            y += 21

        ui.text(d, (cx, 216), "A: RETRY     B: TITLE", 12, anchor="mm")
        return img

    def frame(self, dt, inp):
        self.t += dt
        if self.t < config.RESULT_INPUT_DELAY:
            return
        if inp.pressed("a"):
            self.next = CountdownState(self.game, RaceSession(self.game))
        elif inp.pressed("b"):
            self.next = TitleState(self.game)

    def draw(self, fps):
        return self.img
