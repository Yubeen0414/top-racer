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

# 카메라
LOOKAHEAD_TIME = 0.35        # 몇 초 앞을 보여줄지
LOOKAHEAD_MAX = 70.0         # 최대로 앞당기는 거리 (픽셀)
CAMERA_SMOOTH = 6.0          # 카메라 따라오는 속도 (클수록 딱 붙음)

# 차 그림
CAR_LENGTH = 22
CAR_WIDTH = 12
ROTATION_STEPS = 64          # 미리 만들어 둘 회전 이미지 개수
SPEED_TO_KMH = 0.9           # 화면에 표시할 속도 환산값

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
DEBUG_CHECKPOINTS = False    # True면 트랙에 체크포인트 위치를 노란 선으로 표시
