"""화면 출력과 버튼 입력.

파이에서는 Adafruit 1.3" TFT 보넷을, PC에서는 pygame 창을 써요.
게임 코드는 이 파일만 거치니까 어디서 실행해도 똑같이 동작해요.
"""
import os

import config

BUTTONS = ("up", "down", "left", "right", "center", "a", "b")


class PiHardware:
    def __init__(self):
        import board
        import digitalio
        from adafruit_rgb_display import st7789

        self.disp = st7789.ST7789(
            board.SPI(),
            height=240, y_offset=80, rotation=180,
            cs=digitalio.DigitalInOut(board.CE0),
            dc=digitalio.DigitalInOut(board.D25),
            rst=digitalio.DigitalInOut(board.D24),
            baudrate=config.SPI_BAUDRATE,
        )
        self._backlight = digitalio.DigitalInOut(board.D26)
        self._backlight.switch_to_output()
        self._backlight.value = True

        pins = {
            "up": board.D17, "down": board.D22,
            "left": board.D27, "right": board.D23,
            "center": board.D4, "a": board.D5, "b": board.D6,
        }
        self._buttons = {}
        for name, pin in pins.items():
            b = digitalio.DigitalInOut(pin)
            b.direction = digitalio.Direction.INPUT
            b.pull = digitalio.Pull.UP
            self._buttons[name] = b
        self.running = True  # 파이에서는 Ctrl+C로 종료
        import numpy
        self._np = numpy
        self._fast_show = True

    def read_input(self):
        # 보넷 버튼은 누르면 False
        return {name: not b.value for name, b in self._buttons.items()}

    def show(self, image):
        """화면 전송. 라이브러리의 disp.image()는 픽셀 11만 개를 파이썬 리스트로 바꿨다가
        다시 바이트로 바꿔서 느려요. 같은 변환(회전 + RGB565)을 numpy로 바로 바이트로 만들어서 보내요."""
        if self._fast_show:
            try:
                rot = self.disp.rotation
                if rot:
                    image = image.rotate(rot, expand=True)      # 라이브러리와 똑같이 돌려요
                w, h = image.size
                data = self._np.asarray(image.convert("RGB"), dtype=self._np.uint16)
                c = ((data[:, :, 0] & 0xF8) << 8) | ((data[:, :, 1] & 0xFC) << 3) | (data[:, :, 2] >> 3)
                self.disp._block(0, 0, w - 1, h - 1, c.astype(">u2").tobytes())
                return
            except Exception as e:                            # 라이브러리 버전이 달라 실패하면 원래 방식으로
                print("[hardware] 빠른 화면 전송 실패, 기본 방식으로 전환:", e)
                self._fast_show = False
        self.disp.image(image)

    def close(self):
        from PIL import Image
        self.disp.image(Image.new("RGB", (config.SCREEN_W, config.SCREEN_H)))


class PCHardware:
    """키보드: 방향키 = 조이스틱, Z/Space = A, X = B, Enter = 가운데, Esc = 종료"""

    def __init__(self):
        import pygame
        self.pg = pygame
        pygame.init()
        size = (config.SCREEN_W * config.PC_SCALE, config.SCREEN_H * config.PC_SCALE)
        self.screen = pygame.display.set_mode(size)
        pygame.display.set_caption("Top Racer (PC)")
        k = pygame
        self.keymap = {
            "up": [k.K_UP], "down": [k.K_DOWN],
            "left": [k.K_LEFT], "right": [k.K_RIGHT],
            "center": [k.K_RETURN],
            "a": [k.K_z, k.K_SPACE], "b": [k.K_x],
        }
        self.running = True

    def read_input(self):
        pg = self.pg
        for e in pg.event.get():
            if e.type == pg.QUIT or (e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE):
                self.running = False
        keys = pg.key.get_pressed()
        return {name: any(keys[c] for c in codes) for name, codes in self.keymap.items()}

    def show(self, image):
        surf = self.pg.image.frombuffer(image.tobytes(), image.size, "RGB")
        surf = self.pg.transform.scale(surf, self.screen.get_size())
        self.screen.blit(surf, (0, 0))
        self.pg.display.flip()

    def close(self):
        self.pg.quit()


def create():
    """파이면 보넷, 아니면 PC 창. 환경변수 FORCE_PC=1 이면 무조건 PC 모드."""
    if os.environ.get("FORCE_PC") != "1":
        try:
            import board  # noqa: F401  (파이에서만 import 성공)
        except (ImportError, NotImplementedError, RuntimeError):
            pass
        else:
            return PiHardware()
    return PCHardware()


class Input:
    """held(): 누르고 있는 동안 계속 True / pressed(): 누른 순간 한 번만 True"""

    def __init__(self, hw):
        self.hw = hw
        self.now = {n: False for n in BUTTONS}
        self.prev = dict(self.now)

    def update(self):
        self.prev = self.now
        self.now = self.hw.read_input()

    def held(self, name):
        return self.now[name]

    def pressed(self, name):
        return self.now[name] and not self.prev[name]
