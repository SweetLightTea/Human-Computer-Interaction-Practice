"""
键盘输入映射模块 - Keyboard Input Simulation

将手势识别结果映射为键盘按键，发送给 Unity 游戏窗口。

映射关系（对应现有 Unity 代码的输入）:
  - MoveDirection.LEFT   → 按住 A 键 (Input.GetAxisRaw("Horizontal") = -1)
  - MoveDirection.RIGHT  → 按住 D 键 (Input.GetAxisRaw("Horizontal") = +1)
  - MoveDirection.NONE   → 释放 A/D 键
  - is_jumping == True   → 点按 Space 键 (Input.GetKeyDown(KeyCode.Space))

Unity 输入对应:
  - PlayerState.cs:  xInput = Input.GetAxisRaw("Horizontal")  → A/D 键
  - PlayerGroundState.cs: Input.GetKeyDown(KeyCode.Space)     → Space 键

键盘模拟策略:
  优先使用 pydirectinput（DirectInput scancode，兼容大多数游戏），
  如果不可用则回退到 pynput / ctypes SendInput。
"""

import time
from enum import Enum, auto
from typing import Optional

from gesture_detector import GestureResult, MoveDirection


class KeyState(Enum):
    """按键状态"""
    PRESSED = auto()
    RELEASED = auto()


class InputMapper:
    """
    手势到键盘的映射器

    维护当前按键状态，仅在状态变化时发送键盘事件，
    避免重复发送相同按键。
    """

    # 按键映射配置
    KEY_LEFT = "a"       # 左移 → A 键
    KEY_RIGHT = "d"      # 右移 → D 键
    KEY_JUMP = "space"   # 跳跃 → 空格键

    # 可选：使用方向键代替字母键
    # KEY_LEFT = "left"
    # KEY_RIGHT = "right"

    def __init__(self, use_direct_input: bool = True):
        """
        初始化输入映射器。

        Args:
            use_direct_input: True=使用 pydirectinput, False=尝试其他方式
        """
        self._current_move: MoveDirection = MoveDirection.NONE
        self._keyboard = None
        self._use_direct_input = use_direct_input

        if use_direct_input:
            try:
                import pydirectinput
                # 设置 pydirectinput 的按键间隔（秒）
                pydirectinput.FAILSAFE = False
                pydirectinput.PAUSE = 0.0
                self._keyboard = pydirectinput
                self._backend = "pydirectinput"
            except ImportError:
                print("[InputMapper] pydirectinput 未安装，尝试回退方案...")
                self._use_direct_input = False

        if not self._use_direct_input or self._keyboard is None:
            # 回退方案1: pynput
            try:
                from pynput.keyboard import Key, Controller
                self._pynput_kb = Controller()
                self._backend = "pynput"
                # pynput 的按键映射
                self._pynput_keys = {
                    self.KEY_LEFT: self.KEY_LEFT,
                    self.KEY_RIGHT: self.KEY_RIGHT,
                    self.KEY_JUMP: Key.space,
                }
            except ImportError:
                # 回退方案2: ctypes SendInput (Windows)
                self._backend = "ctypes_sendinput"
                print("[InputMapper] 使用 ctypes SendInput 方案")

    # ---- 公共接口 ----

    def apply_gesture(self, gesture: GestureResult) -> None:
        """
        根据手势识别结果发送对应的键盘输入。

        Args:
            gesture: 手势识别结果
        """
        if not gesture.hand_detected:
            # 手未检测到 → 释放所有按键
            self._release_all()
            return

        self._update_movement(gesture.move_direction)
        self._update_jump(gesture.is_jumping)

    def release_all(self) -> None:
        """释放所有当前按下的按键（安全清理）"""
        self._release_all()

    # ---- 内部方法 ----

    def _update_movement(self, direction: MoveDirection) -> None:
        """
        根据移动方向更新键盘状态。

        只在方向改变时发送按键事件，避免每帧重复按下/释放。
        """
        if direction == self._current_move:
            return  # 状态未变，无需操作

        # 先释放之前的移动键
        if self._current_move == MoveDirection.LEFT:
            self._key_up(self.KEY_LEFT)
        elif self._current_move == MoveDirection.RIGHT:
            self._key_up(self.KEY_RIGHT)

        # 按下新的移动键
        if direction == MoveDirection.LEFT:
            self._key_down(self.KEY_LEFT)
        elif direction == MoveDirection.RIGHT:
            self._key_down(self.KEY_RIGHT)

        self._current_move = direction

    def _update_jump(self, should_jump: bool) -> None:
        """
        处理跳跃输入。

        跳跃是一次性动作：按下并立即释放 Space 键。
        """
        if should_jump:
            self._key_tap(self.KEY_JUMP)

    def _release_all(self) -> None:
        """释放所有可能的按键"""
        if self._current_move == MoveDirection.LEFT:
            self._key_up(self.KEY_LEFT)
        elif self._current_move == MoveDirection.RIGHT:
            self._key_up(self.KEY_RIGHT)
        self._current_move = MoveDirection.NONE

    # ---- 底层键盘操作 ----

    def _key_down(self, key: str) -> None:
        """按下按键"""
        if self._backend == "pydirectinput":
            self._keyboard.keyDown(key)
        elif self._backend == "pynput":
            self._pynput_kb.press(self._pynput_keys.get(key, key))
        else:
            self._send_key_ctypes(key, press=True, release=False)

    def _key_up(self, key: str) -> None:
        """释放按键"""
        if self._backend == "pydirectinput":
            self._keyboard.keyUp(key)
        elif self._backend == "pynput":
            self._pynput_kb.release(self._pynput_keys.get(key, key))
        else:
            self._send_key_ctypes(key, press=False, release=True)

    def _key_tap(self, key: str) -> None:
        """点按按键（按下并立即释放）"""
        if self._backend == "pydirectinput":
            self._keyboard.press(key)
        elif self._backend == "pynput":
            self._pynput_kb.press(self._pynput_keys.get(key, key))
            self._pynput_kb.release(self._pynput_keys.get(key, key))
        else:
            self._send_key_ctypes(key, press=True, release=True)

    # ---- Windows ctypes SendInput 回退方案 ----

    @staticmethod
    def _send_key_ctypes(key: str, press: bool = True, release: bool = True) -> None:
        """
        通过 Windows SendInput API 发送键盘事件。

        这是最低层级的回退方案，直接与系统键盘驱动交互。
        """
        import ctypes
        from ctypes import wintypes

        # 虚拟键码映射
        _VK_MAP = {
            "a": 0x41, "d": 0x44, "space": 0x20,
            "left": 0x25, "right": 0x27, "up": 0x26, "down": 0x28,
        }

        vk = _VK_MAP.get(key.lower(), 0)
        if vk == 0:
            return

        # SendInput 结构体定义
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

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
            ]

        class HARDWAREINPUT(ctypes.Structure):
            _fields_ = [
                ("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD),
            ]

        class INPUT_UNION(ctypes.Union):
            _fields_ = [
                ("mi", MOUSEINPUT),
                ("ki", KEYBDINPUT),
                ("hi", HARDWAREINPUT),
            ]

        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", wintypes.DWORD),
                ("union", INPUT_UNION),
            ]

        events = []
        if press:
            inp = INPUT()
            inp.type = 1  # INPUT_KEYBOARD
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
            inp.union.ki.dwFlags = 0x0002  # KEYEVENTF_KEYUP
            inp.union.ki.time = 0
            inp.union.ki.dwExtraInfo = None
            events.append(inp)

        if events:
            n = len(events)
            INPUT_ARRAY = INPUT * n
            ctypes.windll.user32.SendInput(n, INPUT_ARRAY(*events), ctypes.sizeof(INPUT))
