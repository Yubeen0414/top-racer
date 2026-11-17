"""기록 저장 (save_data.json).

트랙마다 저장하는 것:
  best_lap    최고 랩 기록 (초)
  best_total  최고 총 기록 (초)
  splits      최고 랩의 체크포인트 통과 시각 (구간 기록 비교용)
  ghost       최고 랩의 고스트 경로
  key         물리 수치 + 트랙 모양으로 만든 '지문'

config.py의 물리 값이나 트랙 모양을 바꾸면 지문이 달라져서 예전 기록은 자동으로 무시해요.
다른 규칙으로 달린 기록과 비교하면 불공정하니까요.
파일이 없거나 깨져도 게임은 멈추지 않고 빈 기록으로 시작해요 (깨진 파일은 .bak으로 보관).
"""
import hashlib
import json
import os

import config

VERSION = 1
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.SAVE_FILE)

# 이 값들이 바뀌면 기록이 달라지니까 지문에 넣어요. (화면/카메라 설정은 기록과 무관해서 제외)
RECORD_KEYS = (
    "PHYSICS_HZ", "ROAD_WIDTH", "CURB_WIDTH", "WALL_THICKNESS", "WORLD_W", "WORLD_H",
    "ACCEL", "BRAKE", "REVERSE_ACCEL", "MAX_SPEED", "MAX_REVERSE", "DRAG", "GRIP",
    "TURN_RATE", "TURN_FULL_SPEED", "GRASS_MAX_SPEED", "GRASS_DRAG", "WALL_BOUNCE",
    "CAR_WIDTH", "START_BACK", "CHECKPOINT_MAX_JUMP",
    "DRIFT_MIN_SPEED", "DRIFT_END_SPEED", "DRIFT_GRIP", "DRIFT_TURN_MULT", "DRIFT_HANDBRAKE",
    "BOOST_SEGMENTS", "BOOST_CHARGE", "BOOST_SEC", "BOOST_SPEED_MULT", "BOOST_ACCEL",
    "BOOST_GRASS_LOSS", "BOOST_WALL_LOSS",
)


def fingerprint(track_data):
    values = [getattr(config, k) for k in RECORD_KEYS]
    blob = json.dumps([values, track_data["points"], track_data["laps"], track_data["checkpoints"]])
    return hashlib.sha1(blob.encode()).hexdigest()[:12]


def _valid(rec):
    """저장된 기록 하나가 쓸 수 있는 모양인지 (손으로 고쳤거나 깨졌을 때 대비)"""
    try:
        for k in ("best_lap", "best_total"):
            if rec.get(k) is not None:
                float(rec[k])
        for x, y, h in rec.get("ghost", []):
            float(x), float(y), float(h)
        [float(s) for s in rec.get("splits", [])]
        return True
    except (TypeError, ValueError, AttributeError):
        return False


class SaveData:
    def __init__(self, path=PATH):
        self.path = path
        self.data = self._load()

    def _fresh(self):
        return {"version": VERSION, "tracks": {}}

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                d = json.load(f)
            if not isinstance(d, dict) or d.get("version") != VERSION or not isinstance(d.get("tracks"), dict):
                raise ValueError("unknown format")
            return d
        except FileNotFoundError:
            return self._fresh()
        except (OSError, ValueError) as e:      # json 오류도 ValueError
            print(f"[save] 저장 파일을 읽을 수 없어 새로 시작해요 ({e}). 기존 파일은 .bak으로 보관")
            try:
                os.replace(self.path, self.path + ".bak")
            except OSError:
                pass
            return self._fresh()

    def record(self, track):
        """이 트랙의 기록 (없거나 물리/트랙이 바뀌었으면 None)."""
        rec = self.data["tracks"].get(track.name)
        if not isinstance(rec, dict) or rec.get("key") != track.key or not _valid(rec):
            return None
        return rec

    def update(self, track, **fields):
        rec = self.record(track) or {"key": track.key}
        rec.update(fields)
        self.data["tracks"][track.name] = rec
        self._write()
        return rec

    def _write(self):
        # 임시 파일에 다 쓴 다음 바꿔치기: 쓰는 도중 전원이 꺼져도 기존 파일이 깨지지 않게
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, separators=(",", ":"))
            os.replace(tmp, self.path)
        except OSError as e:
            print(f"[save] 저장 실패: {e}")
