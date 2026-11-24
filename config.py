# ===== 게임 설정값 =====
# 조작감은 거의 전부 여기 숫자로 조절해요.

# 화면
SCREEN_W = 240
SCREEN_H = 240
TARGET_FPS = 30
PC_SCALE = 3                 # PC 창 확대 배율 (240x240 -> 720x720)

# 디스플레이 (파이)
SPI_BAUDRATE = 24_000_000    # 화면이 깨지면 16_000_000 또는 8_000_000 으로 낮추기

# 월드 / 트랙
WORLD_W = 960
WORLD_H = 960
ROAD_WIDTH = 70              # 도로 폭 (차 폭의 약 6배)
CURB_WIDTH = 6               # 연석 폭 (빨강/흰색)
WALL_THICKNESS = 12          # 맵 가장자리 벽 두께

# 차량 물리 (단위: 픽셀/초)
ACCEL = 260.0                # 가속
BRAKE = 420.0                # 브레이크
REVERSE_ACCEL = 160.0        # 후진 가속
MAX_SPEED = 230.0            # 최고 속도
MAX_REVERSE = 70.0           # 최고 후진 속도
DRAG = 0.6                   # 자연 감속 (클수록 빨리 멈춤)
GRIP = 7.0                   # 접지력 (작을수록 많이 미끄러짐 = 드리프트)
TURN_RATE = 3.2              # 최대 회전 속도 (라디안/초)
TURN_FULL_SPEED = 60.0       # 이 속도 이상이어야 조향이 100% 들어감
GRASS_MAX_SPEED = 110.0      # 잔디 위 최고 속도
GRASS_DRAG = 2.5             # 잔디 추가 감속
WALL_BOUNCE = 0.35           # 벽에 부딪혔을 때 튕기는 정도
SAND_MAX_SPEED = 75.0        # 모래 위 최고 속도 (잔디보다 훨씬 느림)
SAND_DRAG = 4.0              # 모래 추가 감속
SAND_CORNER_TURN = 0.55     # 중심선이 이만큼(라디안) 이상 꺾이는 코너 바깥에 모래 (sand 켠 트랙)

# 조작 방식 (기록과 무관해서 바꿔도 저장된 기록은 그대로예요)
#   "rotate"   : 화면이 차를 따라 돌아서 차가 항상 위를 봐요. 조이스틱 좌/우 = 운전석 기준 좌/우 (추천)
#   "absolute" : 조이스틱을 민 방향(화면 기준)으로 차가 돌아요. 위로 밀면 화면 위쪽으로 달려요.
#                조이스틱 위가 조향에 쓰이니까 부스트 = 가운데 짧게, 일시정지 = 가운데 길게
#   "classic"  : 예전 방식. 화면 고정, 좌/우 = 차 기준 회전
CONTROL_MODE = "rotate"
CAMERA_TURN_SMOOTH = 5.0     # (rotate) 화면이 차 방향을 따라 도는 속도 (클수록 딱 붙음, 작을수록 부드러움)
CAMERA_ROTATE_FAST = False   # (rotate) 파이에서 느리면 True (화면 회전을 거칠지만 빠르게)
ABS_DRIFT_MIN_ANGLE = 0.35   # (absolute) 차 방향과 조이스틱 방향이 이만큼(라디안) 이상 달라야 드리프트 시작
PAUSE_HOLD_SEC = 0.6         # (absolute) 가운데 버튼을 이만큼 누르고 있으면 일시정지

# 카메라
LOOKAHEAD_TIME = 0.35        # 몇 초 앞을 보여줄지
LOOKAHEAD_MAX = 70.0         # 최대로 앞당기는 거리 (픽셀)
CAMERA_SMOOTH = 6.0          # 카메라 따라오는 속도 (클수록 딱 붙음)

# 차 그림
CAR_LENGTH = 22
CAR_WIDTH = 12
ROTATION_STEPS = 64          # 미리 만들어 둘 회전 이미지 개수
SPEED_TO_KMH = 0.9           # 화면에 표시할 속도 환산값

# 드리프트 (고속에서 B를 누르며 조향, B는 짧게 눌러도 되고 계속 눌러도 돼요)
DRIFT_MIN_SPEED = 120.0      # 이 속도 이상에서만 드리프트 시작
DRIFT_END_SPEED = 60.0       # 이 아래로 느려지면 드리프트 끝
DRIFT_RELEASE_GRACE = 0.25   # 조향을 이 시간 넘게 놓고 있어야 드리프트 끝 (방향 고쳐 잡는 동안 안 끊기게)
DRIFT_GRIP = 3.0             # 드리프트 중 접지력 (작을수록 많이 미끄러짐)
DRIFT_TURN_MULT = 1.25       # 드리프트 중 회전 속도 배율
DRIFT_KEEP = 0.8             # 옆으로 미끄러지며 잃는 속도 중 앞으로 되돌려주는 비율 (클수록 속도 유지)
DRIFT_SLIP_FULL = 0.35       # 이만큼 미끄러지면 게이지가 최대 속도로 참

# 부스트
BOOST_SEGMENTS = 3           # 게이지 칸 수 (부스트 1번 = 1칸)
BOOST_CHARGE = 0.8           # 드리프트로 게이지가 차는 속도 (칸/초, 충분히 미끄러질 때)
BOOST_SEC = 1.5              # 부스트 지속 시간
BOOST_SPEED_MULT = 1.3       # 부스트 중 최고 속도 배율
BOOST_ACCEL = 300.0          # 부스트 중 추가 가속
BOOST_GRASS_LOSS = 0.8       # 드리프트 중 잔디에 있으면 초당 잃는 칸
BOOST_WALL_LOSS = 0.5        # 드리프트 중 벽에 부딪히면 한 번에 잃는 칸

# 고스트 / 구간 기록 / 저장
GHOST_HZ = 15                # 고스트 위치를 1초에 몇 번 기록할지
GHOST_ALPHA = 110            # 고스트 투명도 (0=안 보임, 255=불투명)
GHOST_SNAP_DIST = 60.0       # 기록 사이가 이보다 멀면(복귀 버튼) 미끄러지듯 보간하지 않고 바로 이동
SPLIT_SHOW_SEC = 2.0         # 구간 기록 차이(+0.31) 보여주는 시간
SAVE_FILE = "save_data.json"

# 고정 시간 간격 물리
PHYSICS_HZ = 60              # 물리는 1초에 항상 이만큼 계산 (화면 FPS와 무관)
MAX_STEPS_PER_FRAME = 5      # 너무 밀리면 따라잡기를 포기 (느린 기기에서 멈춤 방지)

# 레이스 진행
START_BACK = 14              # 출발선에서 몇 픽셀 뒤에 차를 세울지
COUNTDOWN_SEC = 3            # 3, 2, 1
GO_SHOW_SEC = 0.8            # GO! 글자 보여주는 시간
LAP_BANNER_SEC = 2.0         # 랩 완료 알림 보여주는 시간
FINISH_SHOW_SEC = 2.0        # FINISH! 후 결과 화면까지
RESULT_INPUT_DELAY = 1.0     # 결과 화면에서 버튼을 받기 시작하는 시간 (실수로 넘어가지 않게)

# 체크포인트 / 역주행
CHECKPOINT_MAX_JUMP = 6      # 한 번에 중심선 점을 이만큼 넘게 건너뛰면 무효 (지름길 방지)
WRONG_WAY_SPEED = 25.0       # 트랙 반대 방향으로 이 속도 이상이면 역주행 후보
WRONG_WAY_TIME = 0.8         # 이 시간 넘게 계속되면 WRONG WAY 표시

# 개발용
SHOW_FPS = True
PROFILE = False              # True면 5초마다 터미널에 FPS와 (갱신/그리기/전송) 시간 출력
DEBUG_CHECKPOINTS = False    # True면 트랙에 체크포인트 위치를 노란 선으로 표시
