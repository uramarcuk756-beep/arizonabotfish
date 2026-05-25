"""
ArizonaFish Bot — Android Overlay APK
Поверх игры показывает прямоугольник-зону.
Детектирует кнопку PRESS KEY N/H и автонажимает.
"""

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.core.window import Window
from kivy.utils import platform

import threading
import subprocess
import time
import os
import io

# ── Android-специфика ────────────────────────────────────────
if platform == 'android':
    from android.permissions import request_permissions, Permission
    from jnius import autoclass

    PythonActivity   = autoclass('org.kivy.android.PythonActivity')
    Context          = autoclass('android.content.Context')
    WindowManager    = autoclass('android.view.WindowManager')
    LayoutParams     = autoclass('android.view.WindowManager$LayoutParams')
    PixelFormat      = autoclass('android.graphics.PixelFormat')

    def request_all_permissions():
        request_permissions([
            Permission.READ_EXTERNAL_STORAGE,
            Permission.WRITE_EXTERNAL_STORAGE,
            Permission.FOREGROUND_SERVICE,
            Permission.SYSTEM_ALERT_WINDOW,
        ])
else:
    def request_all_permissions():
        pass

# ── Попытка импорта PIL ───────────────────────────────────────
try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ── Состояние бота ───────────────────────────────────────────
bot_state = {
    'running': False,
    'count':   0,
    'status':  'Выключен',
}

# ── Детектирование кнопки через цвет пикселей ───────────────
def is_press_key_button(path, rx, ry, rw, rh):
    """
    Возвращает True если в зоне (rx,ry,rw,rh) есть кнопка PRESS KEY N/H.
    Логика: центр кнопки красный И правее центра тоже красный
    (у CLICK TO EXIT там белый текст EXIT).
    """
    if not PIL_OK:
        return False
    try:
        img = Image.open(path).convert('RGB')
        sw, sh = img.size

        cx = rx + rw // 2
        cy = ry + rh // 2

        # Центр кнопки — должен быть красным
        r, g, b = img.getpixel((min(cx, sw-1), min(cy, sh-1)))
        if not (r > 140 and g < 80 and b < 80):
            return False

        # Правая часть (62% ширины зоны от левого края зоны)
        px = rx + int(rw * 0.62)
        r2, g2, b2 = img.getpixel((min(px, sw-1), min(cy, sh-1)))

        # PRESS KEY N/H: правее H уже красный фон → True
        # CLICK TO EXIT: там белая буква T/I → False
        return r2 > 140 and g2 < 80 and b2 < 80
    except Exception:
        return False

# ── Скриншот ─────────────────────────────────────────────────
SCREEN_PATH = '/sdcard/arizona_bot_screen.png'

def take_screenshot():
    try:
        subprocess.run(
            ['screencap', '-p', SCREEN_PATH],
            timeout=3, capture_output=True
        )
        return os.path.exists(SCREEN_PATH)
    except Exception:
        pass
    try:
        subprocess.run(
            ['termux-screenshot', '-f', SCREEN_PATH],
            timeout=5, capture_output=True
        )
        return os.path.exists(SCREEN_PATH)
    except Exception:
        return False

# ── Нажатие на экран ─────────────────────────────────────────
def tap(x, y):
    try:
        subprocess.run(['input', 'tap', str(int(x)), str(int(y))],
                       timeout=2, capture_output=True)
    except Exception:
        pass

# ── Основной цикл бота ───────────────────────────────────────
def bot_loop(get_region, on_status):
    last_tap = 0
    while bot_state['running']:
        try:
            rx, ry, rw, rh = get_region()
            if take_screenshot():
                if is_press_key_button(SCREEN_PATH, rx, ry, rw, rh):
                    now = time.time()
                    if now - last_tap > 0.8:
                        cx = rx + rw // 2
                        cy = ry + rh // 2
                        tap(cx, cy)
                        last_tap = now
                        bot_state['count'] += 1
                        on_status(f"✓ Подсечка #{bot_state['count']}")
                else:
                    on_status(f"Жду... ({bot_state['count']} подсечек)")
        except Exception as e:
            on_status(f"Ошибка: {e}")
        time.sleep(0.15)

# ════════════════════════════════════════════════════════════
#  UI — прямоугольник с ручками для resize и drag
# ════════════════════════════════════════════════════════════
HANDLE = 36   # px — размер уголков

class SelectionRect(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rx = 60
        self.ry = 200
        self.rw = 500
        self.rh = 130

        self._drag_start = None
        self._resize_corner = None
        self.redraw()

    def redraw(self):
        self.canvas.clear()
        with self.canvas:
            # Полупрозрачная заливка зоны
            Color(1, 0.2, 0.2, 0.12)
            Rectangle(pos=(self.rx, self.ry), size=(self.rw, self.rh))

            # Рамка
            Color(1, 0.15, 0.15, 0.95)
            Line(rectangle=(self.rx, self.ry, self.rw, self.rh), width=2.5)

            # Подпись
            Color(1, 1, 1, 0.85)

            # Уголки (drag handles)
            Color(1, 0.9, 0.1, 1)
            corners = self._corners()
            for cx, cy in corners:
                RoundedRectangle(
                    pos=(cx - HANDLE//2, cy - HANDLE//2),
                    size=(HANDLE, HANDLE),
                    radius=[6]
                )

    def _corners(self):
        return [
            (self.rx,           self.ry),
            (self.rx + self.rw, self.ry),
            (self.rx,           self.ry + self.rh),
            (self.rx + self.rw, self.ry + self.rh),
        ]

    def _hit_corner(self, tx, ty):
        for i, (cx, cy) in enumerate(self._corners()):
            if abs(tx - cx) < HANDLE and abs(ty - cy) < HANDLE:
                return i
        return None

    def _inside(self, tx, ty):
        return (self.rx < tx < self.rx + self.rw and
                self.ry < ty < self.ry + self.rh)

    def on_touch_down(self, touch):
        c = self._hit_corner(touch.x, touch.y)
        if c is not None:
            self._resize_corner = c
            self._drag_start = None
            return True
        if self._inside(touch.x, touch.y):
            self._drag_start = (touch.x - self.rx, touch.y - self.ry)
            self._resize_corner = None
            return True
        return False

    def on_touch_move(self, touch):
        if self._resize_corner is not None:
            i = self._resize_corner
            if i == 0:   # левый нижний
                dw = self.rx + self.rw - touch.x
                dh = self.ry + self.rh - touch.y
                self.rx, self.ry = touch.x, touch.y
                self.rw, self.rh = max(80, dw), max(50, dh)
            elif i == 1: # правый нижний
                self.rw = max(80, touch.x - self.rx)
                dh = self.ry + self.rh - touch.y
                self.ry = touch.y
                self.rh = max(50, dh)
            elif i == 2: # левый верхний
                dw = self.rx + self.rw - touch.x
                self.rx = touch.x
                self.rw = max(80, dw)
                self.rh = max(50, touch.y - self.ry)
            elif i == 3: # правый верхний
                self.rw = max(80, touch.x - self.rx)
                self.rh = max(50, touch.y - self.ry)
            self.redraw()
            return True
        if self._drag_start:
            ox, oy = self._drag_start
            self.rx = touch.x - ox
            self.ry = touch.y - oy
            self.redraw()
            return True
        return False

    def on_touch_up(self, touch):
        self._drag_start = None
        self._resize_corner = None
        return False

    def get_region_screen(self):
        """Координаты в пикселях экрана (Kivy Y перевёрнут)"""
        sw, sh = Window.size
        # Kivy (0,0) — левый нижний, Android — левый верхний
        return (
            int(self.rx),
            int(sh - self.ry - self.rh),
            int(self.rw),
            int(self.rh),
        )

# ════════════════════════════════════════════════════════════
#  Панель управления
# ════════════════════════════════════════════════════════════
class ControlPanel(BoxLayout):
    def __init__(self, sel_rect, **kwargs):
        super().__init__(orientation='horizontal', size_hint=(1, None),
                         height=56, spacing=6, padding=[6, 4], **kwargs)
        self.sel = sel_rect
        self._thread = None

        self.lbl = Label(
            text='[b]ArizonaFish[/b]  |  Выключен',
            markup=True, font_size=14,
            color=(1, 1, 1, 1), size_hint=(1, 1)
        )

        self.btn = Button(
            text='▶ СТАРТ',
            size_hint=(None, 1), width=110,
            background_color=(0.15, 0.75, 0.15, 1),
            font_size=15, bold=True
        )
        self.btn.bind(on_press=self.toggle)

        self.add_widget(self.lbl)
        self.add_widget(self.btn)

    def toggle(self, *_):
        if bot_state['running']:
            bot_state['running'] = False
            self.btn.text = '▶ СТАРТ'
            self.btn.background_color = (0.15, 0.75, 0.15, 1)
            self.set_status('Остановлен')
        else:
            bot_state['running'] = True
            bot_state['count']   = 0
            self.btn.text = '⏹ СТОП'
            self.btn.background_color = (0.8, 0.15, 0.15, 1)
            self.set_status('Запускаю...')
            self._thread = threading.Thread(
                target=bot_loop,
                args=(self.sel.get_region_screen, self.set_status),
                daemon=True
            )
            self._thread.start()

    def set_status(self, text):
        def _update(dt):
            self.lbl.text = f'[b]ArizonaFish[/b]  |  {text}'
        Clock.schedule_once(_update, 0)

# ════════════════════════════════════════════════════════════
#  Главный виджет
# ════════════════════════════════════════════════════════════
class RootLayout(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.sel = SelectionRect(size_hint=(1, 1))
        self.add_widget(self.sel)

        self.panel = ControlPanel(self.sel, pos_hint={'top': 1})
        self.add_widget(self.panel)

        # Подсказка
        hint = Label(
            text='[i]Тяни углы прямоугольника на кнопку PRESS KEY N[/i]',
            markup=True, font_size=12,
            color=(1, 1, 1, 0.7),
            size_hint=(None, None), size=(400, 30),
            pos_hint={'center_x': 0.5, 'y': 0.01}
        )
        self.add_widget(hint)

# ════════════════════════════════════════════════════════════
#  App
# ════════════════════════════════════════════════════════════
class ArizonaFishApp(App):
    def build(self):
        request_all_permissions()
        Window.clearcolor = (0, 0, 0, 0.18)
        self.title = 'ArizonaFish Bot'
        return RootLayout()

if __name__ == '__main__':
    ArizonaFishApp().run()
