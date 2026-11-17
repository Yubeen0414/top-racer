"""메달과 트랙 해금 규칙.

메달: 3바퀴 총 기록이 트랙의 메달 기준(tracks.py medals) 안이면 금/은/동.
해금: 앞 트랙에서 동메달 이상을 따면 다음 트랙이 열려요. 첫 트랙은 처음부터 열려 있어요.
      해금 상태는 따로 저장해서, 물리 값이 바뀌어 기록이 초기화돼도 열린 트랙은 그대로예요.
"""
MEDALS = ("gold", "silver", "bronze")
MEDAL_COLORS = {
    "gold": (255, 200, 40),
    "silver": (200, 205, 215),
    "bronze": (205, 125, 55),
}


def medal_for(track, total):
    """총 기록으로 받는 메달 ("gold"/"silver"/"bronze"/None)"""
    if total is None or not track.medals:
        return None
    for m in MEDALS:
        if total <= track.medals[m]:
            return m
    return None


def best_medal(game, track):
    rec = game.save.record(track)
    return medal_for(track, rec.get("best_total") if rec else None)


def is_unlocked(game, index):
    return index == 0 or game.tracks[index].name in game.save.unlocked


def sync_unlocks(game):
    """동메달 이상 받은 트랙의 다음 트랙을 열어요. 새로 열린 트랙 이름 목록을 돌려줘요."""
    opened = []
    for i, track in enumerate(game.tracks[:-1]):
        nxt = game.tracks[i + 1]
        if best_medal(game, track) and nxt.name not in game.save.unlocked:
            game.save.unlock(nxt.name)
            opened.append(nxt.name)
    return opened


def all_gold(game):
    return all(best_medal(game, t) == "gold" for t in game.tracks)
