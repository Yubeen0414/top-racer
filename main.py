"""Top Racer : Ghost Lap

조작 (파이)  조이스틱 좌/우 = 조향, A = 가속, B = 브레이크/후진, B+조향 = 드리프트,
             조이스틱 위 = 부스트, 가운데 = 일시정지
조작 (PC)    방향키 좌/우 = 조향, Z 또는 Space = 가속, X = 브레이크, X+방향키 = 드리프트,
             ↑ = 부스트, Enter = 일시정지, Esc = 종료

게임 루프 구조 (고정 시간 간격 물리)
  화면은 기기가 할 수 있는 만큼(최대 TARGET_FPS) 그리고,
  물리는 흐른 시간을 통(acc)에 모아 두었다가 항상 1/60초씩 꺼내서 계산해요.
  그래서 PC(빠름)와 파이(느림)에서 같은 조작이면 같은 결과·같은 기록이 나와요.
"""
import time

import config
import hardware
from save import SaveData
from states import TitleState
from track import Track
from tracks import TRACKS


class Game:
    """게임 전체에서 공유하는 것 (트랙은 만들기 오래 걸리니 시작할 때 한 번만)."""

    def __init__(self, save=None):
        self.tracks = [Track(data) for data in TRACKS]
        self.track_index = 0
        self.save = save or SaveData()

    @property
    def track(self):
        return self.tracks[self.track_index]


class StepInput:
    """물리 스텝에 넘기는 입력.

    한 프레임에 물리 스텝이 2~3번 돌기 때문에, '누른 순간'을 그대로 넘기면
    부스트가 한 번 누름에 두 번 쓰이는 식의 문제가 생겨요.
    그래서 누른 순간은 모아 뒀다가 첫 번째 스텝에서만 True가 되게 해요.
    """

    def __init__(self, inp):
        self.inp = inp
        self.pending = set()

    def collect(self):
        self.pending |= {b for b in hardware.BUTTONS if self.inp.pressed(b)}

    def consume(self):
        self.pending.clear()

    def held(self, name):
        return self.inp.held(name)

    def pressed(self, name):
        return name in self.pending


def run(hw, game):
    inp = hardware.Input(hw)
    sinp = StepInput(inp)
    state = TitleState(game)

    step_dt = 1.0 / config.PHYSICS_HZ
    frame_time = 1.0 / config.TARGET_FPS
    acc = 0.0
    last = time.perf_counter()
    fps = float(config.TARGET_FPS)

    while hw.running:
        now = time.perf_counter()
        dt = min(now - last, 0.25)   # 오래 멈췄다 돌아와도 한꺼번에 몰아서 계산하지 않게
        last = now
        if dt > 0:
            fps = fps * 0.9 + (1.0 / dt) * 0.1

        # 1) 입력은 화면 한 장마다 한 번 읽어요 (누른 순간 판정이 두 번 되지 않게)
        inp.update()
        sinp.collect()
        state.frame(dt, inp)

        # 2) 물리는 1/60초씩 고정 간격으로
        acc += dt
        steps = 0
        while acc >= step_dt and state.next is None:
            state.step(step_dt, sinp)
            sinp.consume()
            acc -= step_dt
            steps += 1
            if steps >= config.MAX_STEPS_PER_FRAME:
                acc = 0.0            # 기기가 너무 느리면 밀린 시간은 버려요
                break

        # 3) 상태가 바뀌었으면 교체
        if state.next is not None:
            state = state.next
            acc = 0.0
            sinp.consume()           # 화면을 바꾼 버튼이 다음 화면에서 또 눌린 걸로 치지 않게

        # 4) 그리기
        hw.show(state.draw(fps))

        # 목표 FPS보다 빠르면 쉬기
        spare = frame_time - (time.perf_counter() - now)
        if spare > 0:
            time.sleep(spare)


def main():
    hw = hardware.create()
    try:
        run(hw, Game())
    except KeyboardInterrupt:
        pass
    finally:
        hw.close()


if __name__ == "__main__":
    main()
