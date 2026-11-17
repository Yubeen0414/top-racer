"""랩, 시간, 체크포인트, 역주행 판정.

차 위치를 트랙 중심선 위 가장 가까운 점 번호(0 ~ n-1)로 바꿔서 생각해요.
이 번호가 앞으로 조금씩 늘어나면서 체크포인트 번호를 '지나가면' 통과로 쳐요.

  - 체크포인트는 순서대로만 인정 (1 -> 2 -> ... -> 0(출발선) = 한 바퀴)
  - 한 번에 번호가 크게 튀면(잔디로 가로지른 지름길) 그 사이 체크포인트는 무효
  - 뒤로 가면서 지나간 건 무시 (출발선 앞뒤로 왔다 갔다 해도 랩이 안 올라가요)

시간은 step()이 불릴 때마다 정확히 dt(1/60초)씩 더해요.
그래서 PC든 파이든 같은 주행이면 같은 기록이 나와요.
"""
import config


class LapTracker:
    def __init__(self, track):
        self.track = track
        self.n = len(track.centerline)
        self.cps = track.checkpoints

    def start(self, car):
        self.idx = self.track.nearest_index(car.x, car.y)
        self.next_cp = 1 if len(self.cps) > 1 else 0   # 다음에 지나야 할 체크포인트
        self.last_cp = 0                               # 마지막으로 지난 체크포인트 (복귀 지점)
        self.lap = 1                                   # 지금 달리는 랩 (1부터)
        self.time = 0.0                                # 레이스 전체 시간
        self.lap_start = 0.0
        self.lap_times = []
        self.splits = []                               # 이번 랩의 체크포인트 통과 시각 (2주차 구간 비교용)
        self.finished = False
        self.wrong_time = 0.0
        self.wrong_way = False

    # ---------- 읽기용 ----------
    @property
    def current_lap_time(self):
        return self.time - self.lap_start

    @property
    def best_lap(self):
        return min(self.lap_times) if self.lap_times else None

    # ---------- 매 물리 스텝 ----------
    def step(self, dt, car):
        """1/60초마다 호출. 랩이 끝나면 "lap", 레이스가 끝나면 "finish"를 돌려줘요."""
        if self.finished:
            return None
        self.time += dt

        event = None
        q = self.track.nearest_index(car.x, car.y)
        p = self.idx
        forward = (q - p) % self.n          # 앞으로 몇 점 움직였는지
        if 0 < forward <= config.CHECKPOINT_MAX_JUMP:
            c = self.cps[self.next_cp]
            if 0 < (c - p) % self.n <= forward:   # p에서 q로 가는 사이에 c가 있으면 통과
                event = self._pass_checkpoint()
        self.idx = q

        self._update_wrong_way(dt, car, q)
        return event

    def _pass_checkpoint(self):
        self.last_cp = self.next_cp
        if self.next_cp != 0:
            self.splits.append(self.current_lap_time)
            self.next_cp = (self.next_cp + 1) % len(self.cps)
            return None

        # 출발선 통과 = 한 바퀴 완료
        self.lap_times.append(self.current_lap_time)
        self.lap_start = self.time
        self.splits = []
        self.next_cp = 1 if len(self.cps) > 1 else 0
        if len(self.lap_times) >= self.track.laps:
            self.finished = True
            self.wrong_way = False
            return "finish"
        self.lap += 1
        return "lap"

    def _update_wrong_way(self, dt, car, q):
        tx, ty = self.track.tangent[q]
        along = car.vx * tx + car.vy * ty     # 트랙 진행 방향으로의 속도 (음수면 거꾸로)
        if along < -config.WRONG_WAY_SPEED:
            self.wrong_time += dt
        else:
            self.wrong_time = max(0.0, self.wrong_time - 2 * dt)
        if self.wrong_time >= config.WRONG_WAY_TIME:
            self.wrong_way = True
        elif self.wrong_time == 0.0:
            self.wrong_way = False

    # ---------- 복귀 ----------
    def respawn_pose(self):
        """마지막으로 지난 체크포인트의 위치와 방향."""
        return self.track.pose_at(self.cps[self.last_cp])

    def respawned(self, car):
        self.idx = self.track.nearest_index(car.x, car.y)
        self.wrong_time = 0.0
        self.wrong_way = False
