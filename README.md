# Top Racer : Ghost Lap (1주차)

라즈베리파이 + Adafruit 1.3" TFT 보넷(240x240)용 탑뷰 타임어택 레이싱 게임.
PC에서도 pygame 창으로 똑같이 실행돼요.

## 실행

**파이**
```bash
source ~/env/bin/activate
cd ~/top-racer
python main.py          # 종료: Ctrl+C
```

**PC (Windows)**
```powershell
pip install pillow numpy pygame
python main.py          # 종료: Esc
```

## 조작

| | 파이 | PC |
|---|---|---|
| 조향 | 조이스틱 좌/우 | ← → |
| 가속 | A 버튼 | Z 또는 Space |
| 브레이크/후진 | B 버튼 | X |
| 마지막 체크포인트로 복귀 | 조이스틱 가운데 | Enter |

결과 화면: A = 다시 달리기, B = 타이틀로

## 게임 흐름

시작 화면 → 3, 2, 1, GO! → 3바퀴 → FINISH! → 결과 화면 (랩별 기록, 최고 랩)

- 체크포인트를 순서대로 다 지나야 한 바퀴로 인정 (지름길, 출발선 왕복 X)
- 거꾸로 달리면 WRONG WAY 경고
- 물리는 항상 1/60초 간격으로 계산 → PC와 파이에서 같은 주행이면 같은 기록

## 파일

| 파일 | 내용 |
|---|---|
| `config.py` | 모든 수치 (조작감, 레이스 진행, 개발용 옵션) |
| `tracks.py` | 트랙 데이터 (모양, 랩 수, 체크포인트 수, 색) |
| `track.py` | 트랙 그림 + 판정 마스크 (0=벽, 1=잔디, 2=도로) + 중심선 계산 |
| `race.py` | 랩, 시간, 체크포인트, 역주행 판정 |
| `states.py` | 화면 상태 (시작, 카운트다운, 레이스, 결과) |
| `car.py` | 차량 물리, 회전 이미지 |
| `camera.py` | 룩어헤드 카메라 |
| `hud.py` | 레이스 화면 정보 (랩, 시간, 속도, 알림) |
| `ui.py` | 폰트, 글자 그리기, 시간 형식 |
| `hardware.py` | 보넷 / pygame 입출력 |
| `main.py` | 게임 루프 (고정 시간 간격 물리) |

## 개발용 옵션 (`config.py`)

- `DEBUG_CHECKPOINTS = True` → 트랙에 체크포인트 위치를 노란 선과 번호로 표시
- `SHOW_FPS = False` → 오른쪽 아래 FPS 숨기기
