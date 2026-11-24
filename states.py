"""게임 화면(상태)들. main.py는 '지금 상태' 하나만 돌려요.

  TitleState -> TrackSelectState -> CountdownState -> RaceState <-> PauseState
                                                       -> ResultState -> (다시 / 트랙 선택)
                                                       -> (세 트랙 모두 금메달) AllGoldState

각 상태가 가진 함수:
  frame(dt, inp)  화면 한 장마다 한 번. 메뉴 버튼, 카메라처럼 기록에 영향 없는 것.
  step(dt, inp)   물리 간격(1/60초)마다 한 번. 차 움직임, 시간 재기처럼 기록에 영향 주는 것.
  draw(fps)       화면에 보낼 그림을 돌려줘요.
상태를 바꾸고 싶으면 self.next 에 다음 상태를 넣으면 main.py가 바꿔줘요.
"""
import math

from PIL import Image, ImageDraw

import config
import hud
import progress
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
        self.medal = None                            # 이번 판 기록으로 받은 메달
        self.unlocked = []                           # 이번 판으로 새로 열린 트랙
        self.newly_all_gold = False                  # 이번 판으로 모든 트랙 금메달 달성

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
            was_all_gold = progress.all_gold(self.game)
            old = self.record.get("best_total")
            if old is None or total < old:
                self.record = save.update(self.track, best_total=total)
                self.new_record = True
            self.medal = progress.medal_for(self.track, total)
            self.unlocked = progress.sync_unlocks(self.game)
            self.newly_all_gold = progress.all_gold(self.game) and not was_all_gold
        return delta

    def render_world(self):
        if config.CONTROL_MODE == "rotate":
            return self._render_rotated()
        x0, y0 = self.cam.top_left()
        frame = self.track.image.crop((x0, y0, x0 + config.SCREEN_W, y0 + config.SCREEN_H))
        if self.ghost and not self.lap.finished:
            self.ghost.draw(frame, self.lap.current_lap_time, x0, y0)
        self.car.draw(frame, x0, y0, flicker=int(self.lap.time * 20))
        return frame

    def _render_rotated(self):
        """차가 항상 위를 보도록 돌린 화면.
        돌려도 모서리가 비지 않게 화면 대각선 크기로 넓게 잘라서 그린 뒤, 돌리고 가운데만 잘라요."""
        sw, sh = config.SCREEN_W, config.SCREEN_H
        R = int(math.hypot(sw, sh)) + 4
        cx, cy = self.cam.x, self.cam.y
        x0, y0 = int(cx - R / 2), int(cy - R / 2)
        big = self.track.image.crop((x0, y0, x0 + R, y0 + R))   # 맵 밖은 검정
        if self.ghost and not self.lap.finished:
            self.ghost.draw(big, self.lap.current_lap_time, x0, y0)
        self.car.draw(big, x0, y0, flicker=int(self.lap.time * 20))

        angle = self.cam.angle if self.cam.angle is not None else self.car.heading
        deg = 90 + math.degrees(angle)          # heading 방향이 화면 위로 오게
        # 카메라 중심(cx, cy)이 R/2에서 조금 어긋난 만큼 회전 중심을 맞춰요
        center = (cx - x0, cy - y0)
        resample = Image.NEAREST if config.CAMERA_ROTATE_FAST else Image.BILINEAR
        big = big.rotate(deg, resample=resample, center=center)
        left, top = int(center[0] - sw / 2), int(center[1] - sh / 2)
        return big.crop((left, top, left + sw, top + sh))


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
        # 트랙별 최고 메달
        n = len(game.tracks)
        for i, t in enumerate(game.tracks):
            hud.medal(d, hud.CX + (i - (n - 1) / 2) * 30, 146, 8, progress.best_medal(game, t))

    def frame(self, dt, inp):
        self.t += dt
        if any(inp.pressed(b) for b in BUTTONS):
            self.next = TrackSelectState(self.game)

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
        self.center_t = 0.0       # (absolute) 가운데 버튼 누르고 있는 시간, None = 뗄 때까지 무시

    def frame(self, dt, inp):
        s = self.s
        s.cam.update(dt, s.car)
        if s.lap.finished:
            return
        if config.CONTROL_MODE != "absolute":
            if inp.pressed("center"):
                self.next = PauseState(self.game, self)
            return
        # absolute: 가운데 짧게 = 부스트, 길게 = 일시정지
        if inp.held("center"):
            if self.center_t is not None:
                self.center_t += dt
                if self.center_t >= config.PAUSE_HOLD_SEC:
                    self.center_t = None
                    self.next = PauseState(self.game, self)
        else:
            if self.center_t:
                s.car.boost_request = True
            self.center_t = 0.0

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
    ITEMS = ("CONTINUE", "RESPAWN", "RESTART", "TRACKS")

    def __init__(self, game, race):
        super().__init__(game)
        self.race = race
        self.sel = 0
        self.bg = _darken(race.draw(0.0), 0.6)    # 멈춘 화면을 어둡게 해서 배경으로

    def _resume(self):
        self.race.next = None
        self.race.center_t = None     # 돌아갈 때 누르고 있던 가운데 버튼이 부스트로 안 들어가게
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
                self.next = TrackSelectState(self.game)

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
        self.s = session
        self.img = self._make(session)

    @staticmethod
    def _make(s):
        img = _darken(s.render_world(), 0.65)
        d = ImageDraw.Draw(img)
        cx = hud.CX
        laps = s.lap.lap_times
        ui.text(d, (cx, 20), "RESULT", 20, anchor="mm", stroke=3)
        ui.text(d, (cx, 44), "TOTAL", 10, (190, 190, 190), anchor="mm", stroke=1)
        ui.text(d, (cx, 64), ui.format_time(s.lap.time), 24, hud.YELLOW, anchor="mm", stroke=3)
        if s.new_record:
            ui.text(d, (cx, 88), "NEW RECORD!", 14, hud.GREEN, anchor="mm", stroke=2)
        elif s.record and s.record.get("best_total") is not None:
            ui.text(d, (cx, 88), "RECORD " + ui.format_time(s.record["best_total"]), 11,
                    (190, 190, 190), anchor="mm", stroke=1)

        # 이번 판 메달 (없으면 다음 메달까지 남은 기준)
        if s.medal:
            hud.medal(d, cx - 52, 114, 9, s.medal)
            ui.text(d, (cx - 36, 114), f"{s.medal.upper()} MEDAL", 14, progress.MEDAL_COLORS[s.medal], anchor="lm")
        elif s.track.medals:
            ui.text(d, (cx, 114), "BRONZE " + ui.format_time(s.track.medals["bronze"]), 11,
                    progress.MEDAL_COLORS["bronze"], anchor="mm", stroke=1)

        best = laps.index(min(laps))
        y = 140
        for i, t in enumerate(laps):
            color = hud.GREEN if i == best else hud.WHITE
            ui.text(d, (50, y), f"LAP {i + 1}", 13, color, anchor="lm")
            ui.text(d, (168, y), ui.format_time(t), 13, color, anchor="rm")
            if i == best:
                ui.text(d, (174, y), "BEST", 9, color, anchor="lm", stroke=1)
            y += 19

        if s.unlocked:
            ui.text(d, (cx, 202), "NEW TRACK: " + s.unlocked[0].upper(), 11, (120, 200, 255), anchor="mm", stroke=2)
        ui.text(d, (cx, 224), "A: RETRY     B: TRACKS", 11, anchor="mm")
        return img

    def frame(self, dt, inp):
        self.t += dt
        if self.t < config.RESULT_INPUT_DELAY:
            return
        if not (inp.pressed("a") or inp.pressed("b")):
            return
        if self.s.newly_all_gold:              # 마지막 금메달이면 엔딩 먼저
            self.next = AllGoldState(self.game)
        elif inp.pressed("a"):
            self.next = CountdownState(self.game, RaceSession(self.game))
        else:
            self.next = TrackSelectState(self.game)

    def draw(self, fps):
        return self.img


# ---------------------------------------------------------------- 트랙 선택
class TrackSelectState(State):
    """좌/우로 트랙 넘기기, A로 출발, B로 타이틀. 잠긴 트랙은 출발 못 해요."""

    def __init__(self, game):
        super().__init__(game)
        self.i = game.track_index
        self.cards = [self._card(i) for i in range(len(game.tracks))]   # 화면에 들어올 때 한 번만 그려요

    def _card(self, i):
        game = self.game
        tr = game.tracks[i]
        locked = not progress.is_unlocked(game, i)
        img = Image.new("RGB", (config.SCREEN_W, config.SCREEN_H), (14, 16, 24))
        d = ImageDraw.Draw(img)
        cx = hud.CX
        ui.text(d, (cx, 10), f"TRACK {i + 1}/{len(game.tracks)}", 11, (170, 170, 170), anchor="mm", stroke=1)

        thumb = tr.thumb if not locked else _darken(tr.thumb, 0.7)
        x0 = cx - thumb.width // 2
        img.paste(thumb, (x0, 22))
        d.rectangle((x0 - 1, 21, x0 + thumb.width, 22 + thumb.height), outline=(90, 90, 110))
        if locked:   # 자물쇠
            d.arc((cx - 12, 62, cx + 12, 90), 180, 360, fill=(220, 220, 220), width=4)
            d.rounded_rectangle((cx - 17, 76, cx + 17, 104), radius=4, fill=(220, 220, 220))
            d.ellipse((cx - 3, 85, cx + 3, 91), fill=(40, 40, 50))
        else:
            # 왼쪽 위에 이 트랙 최고 메달
            hud.medal(d, x0 + 14, 40, 8, progress.best_medal(game, tr))

        if i > 0:
            ui.text(d, (14, 82), "<", 22, anchor="mm", stroke=2)
        if i < len(game.tracks) - 1:
            ui.text(d, (config.SCREEN_W - 14, 82), ">", 22, anchor="mm", stroke=2)

        ui.text(d, (cx, 156), tr.name.upper(), 15, anchor="mm", stroke=2)
        ui.text(d, (cx, 172), tr.data.get("subtitle", ""), 9, (170, 170, 170), anchor="mm", stroke=1)

        if locked:
            prev = game.tracks[i - 1].name.upper()
            ui.text(d, (cx, 192), "LOCKED", 13, hud.RED, anchor="mm", stroke=2)
            ui.text(d, (cx, 208), f"GET BRONZE ON {prev}", 9, (190, 190, 190), anchor="mm", stroke=1)
        else:
            rec = game.save.record(tr)
            best = rec.get("best_total") if rec else None
            ui.text(d, (cx, 190), "RECORD " + ui.format_time(best), 12,
                    hud.GREEN if best is not None else (150, 150, 150), anchor="mm", stroke=1)
            if tr.medals:   # 메달 기준 시간
                for k, m in enumerate(progress.MEDALS):
                    x = 22 + k * 74
                    hud.medal(d, x, 209, 5, m)
                    ui.text(d, (x + 8, 209), ui.format_time(tr.medals[m]), 9, progress.MEDAL_COLORS[m],
                            anchor="lm", stroke=1)
        ui.text(d, (cx, 229), "A: START    B: BACK" if not locked else "B: BACK", 10,
                (200, 200, 200), anchor="mm", stroke=1)
        return img

    def frame(self, dt, inp):
        n = len(self.game.tracks)
        if inp.pressed("left") and self.i > 0:
            self.i -= 1
        elif inp.pressed("right") and self.i < n - 1:
            self.i += 1
        elif inp.pressed("a") and progress.is_unlocked(self.game, self.i):
            self.game.track_index = self.i
            self.next = CountdownState(self.game, RaceSession(self.game))
        elif inp.pressed("b"):
            self.next = TitleState(self.game)

    def draw(self, fps):
        return self.cards[self.i]


# ---------------------------------------------------------------- 엔딩
class AllGoldState(State):
    """세 트랙 모두 금메달을 처음 달성했을 때 한 번 나오는 화면."""

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        img = Image.new("RGB", (config.SCREEN_W, config.SCREEN_H), (16, 14, 30))
        d = ImageDraw.Draw(img)
        rng = __import__("random").Random(4)
        for _ in range(60):   # 반짝이는 배경 점
            x, y = rng.randrange(240), rng.randrange(240)
            d.point((x, y), fill=(255, 230, 150))
        cx = hud.CX
        n = len(game.tracks)
        for i in range(n):
            hud.medal(d, cx + (i - (n - 1) / 2) * 44, 62, 15, "gold")
        ui.text(d, (cx, 116), "ALL GOLD!", 32, progress.MEDAL_COLORS["gold"], anchor="mm", stroke=4)
        ui.text(d, (cx, 148), "TIME ATTACK MASTER", 13, anchor="mm", stroke=2)
        total = sum(game.save.record(t)["best_total"] for t in game.tracks)
        ui.text(d, (cx, 172), "ALL TRACKS " + ui.format_time(total), 11, (190, 190, 190), anchor="mm", stroke=1)
        self.img = img

    def frame(self, dt, inp):
        self.t += dt
        if self.t > config.RESULT_INPUT_DELAY and any(inp.pressed(b) for b in BUTTONS):
            self.next = TrackSelectState(self.game)

    def draw(self, fps):
        img = self.img.copy()
        if self.t > config.RESULT_INPUT_DELAY and int(self.t * 2) % 2 == 0:
            ui.text(ImageDraw.Draw(img), (hud.CX, 212), "PRESS ANY BUTTON", 11, anchor="mm")
        return img
