"""글자 그리기 도우미 (폰트 불러오기, 테두리 글자, 시간 형식)."""
from PIL import ImageFont

FONT_PATHS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",   # 파이 (fonts-dejavu)
    "DejaVuSans-Bold.ttf",
    "arialbd.ttf",                                            # 윈도우
)

_fonts = {}


def font(size):
    """크기별로 한 번만 불러와서 재사용해요."""
    if size not in _fonts:
        for path in FONT_PATHS:
            try:
                _fonts[size] = ImageFont.truetype(path, size)
                break
            except OSError:
                pass
        else:
            _fonts[size] = ImageFont.load_default(size)
    return _fonts[size]


def text(d, xy, s, size, fill=(255, 255, 255), anchor="la", stroke=2):
    """검은 테두리가 있는 글자. anchor: la=왼쪽 위, ra=오른쪽 위, mm=가운데."""
    d.text(xy, s, font=font(size), fill=fill, anchor=anchor,
           stroke_width=stroke, stroke_fill=(0, 0, 0))


def format_time(t):
    """초 -> 0:12.34"""
    if t is None:
        return "-:--.--"
    m = int(t // 60)
    return f"{m}:{t - m * 60:05.2f}"
