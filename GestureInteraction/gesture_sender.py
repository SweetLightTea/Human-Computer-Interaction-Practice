"""
手势数据发送模块 - UDP Gesture Data Sender

将手势识别结果通过 UDP 发送给 Unity 端的 GestureReceiver。
不依赖窗口焦点，Unity C# 内部接收到数据后通过 WinAPI PostMessage 模拟按键。

数据格式 (JSON):
{
  "left_hand": {
    "detected": true/false,
    "move_direction": "LEFT" | "RIGHT" | "NONE",
    "jump": true/false
  },
  "right_hand": {
    "detected": true/false,
    "gesture": "FIST" | "OPEN_PALM" | "THUMB_UP" | "NONE"
  }
}
"""

import socket
import json
from typing import Optional

from gesture_detector import GestureResult


class GestureSender:
    """通过 UDP 将手势数据发送给 Unity"""

    def __init__(self, host: str = "127.0.0.1", port: int = 12345):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._addr = (host, port)
        print(f"[GestureSender] UDP 发送器就绪 → {host}:{port}")

    def send(self, gesture: GestureResult) -> None:
        """将手势结果序列化为 JSON 并通过 UDP 发送"""
        data = {
            "left_hand": {
                "detected": gesture.left_hand_detected,
                "move_direction": gesture.move_direction.name,
                "jump": gesture.is_jumping,
            },
            "right_hand": {
                "detected": gesture.right_hand_detected,
                "gesture": gesture.right_hand_gesture.name,
            },
        }

        json_str = json.dumps(data)
        self._sock.sendto(json_str.encode("utf-8"), self._addr)

    def close(self) -> None:
        """关闭 socket"""
        self._sock.close()
