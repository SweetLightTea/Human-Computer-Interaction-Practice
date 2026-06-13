"""
键盘输入映射模块 - Keyboard & Mouse Input Simulation

将手势识别结果映射为键盘/鼠标输入，发送给 Unity 游戏窗口。

映射关系:
  === 左手（移动/跳跃）===
  MoveDirection.LEFT   → 按住 A 键 (左移)
  MoveDirection.RIGHT  → 按住 D 键 (右移)
  MoveDirection.NONE   → 释放 A/D 键
  is_jumping == True   → 点按 Space 键 (跳跃)

  === 右手（战斗/交互）===
  FIST (握拳)          → 鼠标左键点击 (开火)
  OPEN_PALM (五指张开)  → 鼠标右键点击 (开宝箱/捡宝石)
  THUMB_UP (拇指朝上)   → 点按 Q 键 (装弹)

Unity 输入对应:
  PlayerState.cs:        Input.GetAxisRaw("Horizontal")  → A/D 键
  PlayerGroundState.cs:  Input.GetKeyDown(KeyCode.Space) → Space 键
  PlayerGroundState.cs:  Input.GetMouseButtonDown(0)     → 鼠标左键
  Chest.cs / Diamond.cs: Input.GetMouseButtonDown(1)     → 鼠标右键
  PlayerGroundState.cs:  Input.GetKeyDown(KeyCode.Q)     → Q 键 (装弹)
"""

import time
from enum import Enum, auto
from typing import Optional

from gesture_detector import GestureResult, MoveDirection, RightHandGesture


class KeyState(Enum):
    PRESSED = auto()
    RELEASED = auto()


class InputMapper:
    """
    手势到键盘/鼠标的映射器

    维护当前按键状态，仅在状态变化时发送事件。
    支持持续开火（握拳时周期性点击鼠标左键）。
    """

    # 左手按键映射
    KEY_LEFT = "a"
    KEY_RIGHT = "d"
    KEY_JUMP = "space"

    # 右手按键映射
    KEY_RELOAD = "q"              # 装弹键

    # 冷却时间（秒）
    FIRE_COOLDOWN = 0.25          # 开火间隔（连续握拳时每 250ms 点击一次）
    INTERACT_COOLDOWN = 0.5       # 交互间隔（防止连续打开宝箱）
    RELOAD_COOLDOWN = 1.0         # 装弹间隔（防止连续装弹）

    def __init__(self, use_direct_input: bool = True):
        self._current_move: MoveDirection = MoveDirection.NONE
        self._keyboard = None
        self._mouse = None
        self._use_direct_input = use_direct_input

        # 右手手势状态追踪
        self._current_right_gesture: RightHandGesture = RightHandGesture.NONE
        self._last_fire_time: float = 0.0
        self._last_interact_time: float = 0.0
        self._last_reload_time: float = 0.0
        self._mouse_left_down: bool = False  # 追踪鼠标左键状态（用于 fire tap）

        if use_direct_input:
            try:
                import pydirectinput
                pydirectinput.FAILSAFE = False
                pydirectinput.PAUSE = 0.0
                self._keyboard = pydirectinput
                self._mouse = pydirectinput
                self._backend = "pydirectinput"
            except ImportError:
                print("[InputMapper] pydirectinput 未安装，尝试回退方案...")
                self._use_direct_input = False

        if not self._use_direct_input or self._keyboard is None:
            try:
                from pynput.keyboard import Key, Controller as KbController
                from pynput.mouse import Button, Controller as MouseController
                self._pynput_kb = KbController()
                self._pynput_mouse = MouseController()
                self._backend = "pynput"
                self._pynput_keys = {
                    self.KEY_LEFT: self.KEY_LEFT,
                    self.KEY_RIGHT: self.KEY_RIGHT,
                    self.KEY_JUMP: Key.space,
                    self.KEY_RELOAD: "q",
                }
            except ImportError:
                self._backend = "ctypes_sendinput"
                print("[InputMapper] 使用 ctypes SendInput 方案")

    # ================================================================
    #  公共接口
    # ================================================================

    def apply_gesture(self, gesture: GestureResult) -> None:
        """
        根据手势识别结果发送对应的键盘/鼠标输入。

        Args:
            gesture: 手势识别结果（包含左右手）
        """
        # 左手：移动 + 跳跃
        if gesture.left_hand_detected:
            self._update_movement(gesture.move_direction)
            self._update_jump(gesture.is_jumping)
        else:
            self._release_movement()

        # 右手：战斗/交互
        if gesture.right_hand_detected:
            self._update_right_hand(gesture.right_hand_gesture)
        else:
            self._release_right_hand()

    def release_all(self) -> None:
        """释放所有当前按下的按键（安全清理）"""
        self._release_movement()
        self._release_right_hand()

    # ================================================================
    #  左手：移动 + 跳跃
    # ================================================================

    def _update_movement(self, direction: MoveDirection) -> None:
        if direction == self._current_move:
            return

        if self._current_move == MoveDirection.LEFT:
            self._key_up(self.KEY_LEFT)
        elif self._current_move == MoveDirection.RIGHT:
            self._key_up(self.KEY_RIGHT)

        if direction == MoveDirection.LEFT:
            self._key_down(self.KEY_LEFT)
        elif direction == MoveDirection.RIGHT:
            self._key_down(self.KEY_RIGHT)

        self._current_move = direction

    def _update_jump(self, should_jump: bool) -> None:
        if should_jump:
            self._key_tap(self.KEY_JUMP)

    def _release_movement(self) -> None:
        if self._current_move == MoveDirection.LEFT:
            self._key_up(self.KEY_LEFT)
        elif self._current_move == MoveDirection.RIGHT:
            self._key_up(self.KEY_RIGHT)
        self._current_move = MoveDirection.NONE

    # ================================================================
    #  右手：战斗/交互（核心）
    # ================================================================

    def _update_right_hand(self, gesture: RightHandGesture) -> None:
        """
        根据右手手势触发对应的按键/鼠标操作。

        FIST (握拳):     周期性点击鼠标左键（持续开火）
        OPEN_PALM (张开): 点击鼠标右键（开宝箱/捡宝石），带冷却
        THUMB_UP (拇指):  点按 Q 键（装弹），带冷却
        NONE:             不做任何操作
        """
        now = time.time()

        if gesture == RightHandGesture.FIST:
            # 握拳 = 开火：周期性点击鼠标左键
            self._handle_fire(now)

        elif gesture == RightHandGesture.OPEN_PALM:
            # 五指张开 = 交互：点击鼠标右键（带冷却）
            if now - self._last_interact_time >= self.INTERACT_COOLDOWN:
                self._mouse_click_right()
                self._last_interact_time = now

        elif gesture == RightHandGesture.THUMB_UP:
            # 拇指朝上 = 装弹：点按 Q 键（带冷却）
            if now - self._last_reload_time >= self.RELOAD_COOLDOWN:
                self._key_tap(self.KEY_RELOAD)
                self._last_reload_time = now

        elif gesture == RightHandGesture.NONE:
            # 过渡状态：不做任何操作
            pass

        self._current_right_gesture = gesture

    def _handle_fire(self, now: float) -> None:
        """
        处理开火：周期性点击鼠标左键。
        每次点击 = 按下 + 释放，模拟 GetMouseButtonDown。
        """
        if now - self._last_fire_time >= self.FIRE_COOLDOWN:
            # 点按鼠标左键（按下并立即释放）
            self._mouse_click_left()
            self._last_fire_time = now

    def _release_right_hand(self) -> None:
        """右手离开摄像头：清除状态，停止所有右手操作"""
        self._current_right_gesture = RightHandGesture.NONE
        # 确保鼠标左键被释放
        if self._mouse_left_down:
            self._mouse_up_left()
            self._mouse_left_down = False

    # ================================================================
    #  底层：键盘操作
    # ================================================================

    def _key_down(self, key: str) -> None:
        if self._backend == "pydirectinput":
            self._keyboard.keyDown(key)
        elif self._backend == "pynput":
            self._pynput_kb.press(self._pynput_keys.get(key, key))
        else:
            self._send_key_ctypes(key, press=True, release=False)

    def _key_up(self, key: str) -> None:
        if self._backend == "pydirectinput":
            self._keyboard.keyUp(key)
        elif self._backend == "pynput":
            self._pynput_kb.release(self._pynput_keys.get(key, key))
        else:
            self._send_key_ctypes(key, press=False, release=True)

    def _key_tap(self, key: str) -> None:
        if self._backend == "pydirectinput":
            self._keyboard.press(key)
        elif self._backend == "pynput":
            self._pynput_kb.press(self._pynput_keys.get(key, key))
            self._pynput_kb.release(self._pynput_keys.get(key, key))
        else:
            self._send_key_ctypes(key, press=True, release=True)

    # ================================================================
    #  底层：鼠标操作
    # ================================================================

    def _mouse_click_left(self) -> None:
        """点击鼠标左键（按下+释放，触发 GetMouseButtonDown）"""
        if self._backend == "pydirectinput":
            self._mouse.click(button="left")
        elif self._backend == "pynput":
            self._pynput_mouse.click(Button.left)
        else:
            self._send_mouse_ctypes("left", click=True)

    def _mouse_click_right(self) -> None:
        """点击鼠标右键"""
        if self._backend == "pydirectinput":
            self._mouse.click(button="right")
        elif self._backend == "pynput":
            self._pynput_mouse.click(Button.right)
        else:
            self._send_mouse_ctypes("right", click=True)

    def _mouse_down_left(self) -> None:
        """按下鼠标左键"""
        if self._backend == "pydirectinput":
            self._mouse.mouseDown(button="left")
        elif self._backend == "pynput":
            self._pynput_mouse.press(Button.left)
        else:
            self._send_mouse_ctypes("left", down=True, up=False)

    def _mouse_up_left(self) -> None:
        """释放鼠标左键"""
        if self._backend == "pydirectinput":
            self._mouse.mouseUp(button="left")
        elif self._backend == "pynput":
            self._pynput_mouse.release(Button.left)
        else:
            self._send_mouse_ctypes("left", down=False, up=True)

    # ================================================================
    #  Windows ctypes SendInput 回退方案
    # ================================================================

    @staticmethod
    def _send_key_ctypes(key: str, press: bool = True, release: bool = True) -> None:
        import ctypes
        from ctypes import wintypes

        _VK_MAP = {
            "a": 0x41, "d": 0x44, "space": 0x20,
            "q": 0x51,
            "left": 0x25, "right": 0x27, "up": 0x26, "down": 0x28,
        }
        vk = _VK_MAP.get(key.lower(), 0)
        if vk == 0:
            return

        wintypes.ULONG_PTR = wintypes.WPARAM

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
            ]

        class INPUT_UNION(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]

        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", wintypes.DWORD),
                ("union", INPUT_UNION),
            ]

        events = []
        if press:
            inp = INPUT()
            inp.type = 1
            inp.union.ki.wVk = vk
            inp.union.ki.wScan = 0
            inp.union.ki.dwFlags = 0
            inp.union.ki.time = 0
            inp.union.ki.dwExtraInfo = None
            events.append(inp)

        if release:
            inp = INPUT()
            inp.type = 1
            inp.union.ki.wVk = vk
            inp.union.ki.wScan = 0
            inp.union.ki.dwFlags = 0x0002
            inp.union.ki.time = 0
            inp.union.ki.dwExtraInfo = None
            events.append(inp)

        if events:
            n = len(events)
            INPUT_ARRAY = INPUT * n
            ctypes.windll.user32.SendInput(n, INPUT_ARRAY(*events), ctypes.sizeof(INPUT))

    @staticmethod
    def _send_mouse_ctypes(
        button: str = "left",
        down: bool = False,
        up: bool = False,
        click: bool = False,
    ) -> None:
        """通过 Windows SendInput API 发送鼠标事件"""
        import ctypes
        from ctypes import wintypes

        wintypes.ULONG_PTR = wintypes.WPARAM

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
            ]

        class INPUT_UNION(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT)]

        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", wintypes.DWORD),
                ("union", INPUT_UNION),
            ]

        # 鼠标事件标志
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        MOUSEEVENTF_RIGHTDOWN = 0x0008
        MOUSEEVENTF_RIGHTUP = 0x0010

        if button == "left":
            flags_down = MOUSEEVENTF_LEFTDOWN
            flags_up = MOUSEEVENTF_LEFTUP
        else:
            flags_down = MOUSEEVENTF_RIGHTDOWN
            flags_up = MOUSEEVENTF_RIGHTUP

        events = []

        if down or click:
            inp = INPUT()
            inp.type = 0  # INPUT_MOUSE
            inp.union.mi.dx = 0
            inp.union.mi.dy = 0
            inp.union.mi.mouseData = 0
            inp.union.mi.dwFlags = flags_down
            inp.union.mi.time = 0
            inp.union.mi.dwExtraInfo = None
            events.append(inp)

        if up or click:
            inp = INPUT()
            inp.type = 0
            inp.union.mi.dx = 0
            inp.union.mi.dy = 0
            inp.union.mi.mouseData = 0
            inp.union.mi.dwFlags = flags_up
            inp.union.mi.time = 0
            inp.union.mi.dwExtraInfo = None
            events.append(inp)

        if events:
            n = len(events)
            INPUT_ARRAY = INPUT * n
            ctypes.windll.user32.SendInput(n, INPUT_ARRAY(*events), ctypes.sizeof(INPUT))
