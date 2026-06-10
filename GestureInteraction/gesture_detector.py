"""
手势检测模块 - Hand Detection & Gesture Recognition

使用 MediaPipe Hands 检测手部关键点，识别以下手势：
  1. 左手大拇指方向 → 映射为水平移动方向 (左/右/静止)
  2. 左手四指朝上 → 映射为跳跃动作

MediaPipe 手部关键点索引:
  0:  手腕 (Wrist)
  1:  拇指 CMC
  2:  拇指 MCP
  3:  拇指 IP
  4:  拇指指尖 (Thumb Tip)
  5:  食指 MCP
  6:  食指 PIP
  7:  食指 DIP
  8:  食指指尖 (Index Tip)
  9:  中指 MCP
  10: 中指 PIP
  11: 中指 DIP
  12: 中指指尖 (Middle Tip)
  13: 无名指 MCP
  14: 无名指 PIP
  15: 无名指 DIP
  16: 无名指指尖 (Ring Tip)
  17: 小指 MCP
  18: 小指 PIP
  19: 小指 DIP
  20: 小指指尖 (Pinky Tip)
"""

import cv2
import mediapipe as mp
import numpy as np
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Tuple


class MoveDirection(Enum):
    """水平移动方向"""
    LEFT = auto()
    RIGHT = auto()
    NONE = auto()


@dataclass
class GestureResult:
    """手势识别结果"""
    move_direction: MoveDirection = MoveDirection.NONE
    is_jumping: bool = False
    hand_detected: bool = False
    # 调试信息
    thumb_angle_deg: float = 0.0
    fingers_up_count: int = 0


class HandGestureDetector:
    """
    手部手势检测器

    使用 MediaPipe Hands 从摄像头画面中检测左手，
    并识别预定义的手势动作。
    """

    # ---- 可调参数 ----
    # 拇指方向阈值：拇指尖相对 MCP 关节的水平偏移比例
    # thumb_tip.x - thumb_mcp.x 归一化到手掌尺寸后与此阈值比较
    THUMB_HORIZONTAL_THRESHOLD = 0.08

    # 手指朝上阈值：指尖 y 坐标需要比对应 PIP 关节高多少（归一化值）
    FINGER_UP_THRESHOLD = 0.04

    # 跳跃触发所需的最小朝上手指数量
    MIN_FINGERS_UP_FOR_JUMP = 3

    # 跳跃冷却帧数（防止连续触发）
    JUMP_COOLDOWN_FRAMES = 10

    def __init__(
        self,
        static_image_mode: bool = False,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
    ):
        """
        初始化 MediaPipe Hands 检测器。

        Args:
            static_image_mode: 是否处理静态图片（False=视频流模式）
            max_num_hands: 最大检测手数
            min_detection_confidence: 检测置信度阈值 [0, 1]
            min_tracking_confidence: 追踪置信度阈值 [0, 1]
        """
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=static_image_mode,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_draw_styles = mp.solutions.drawing_styles

        self._jump_cooldown_counter: int = 0

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, GestureResult]:
        """
        处理单帧画面，检测手势并返回标注后的图像和识别结果。

        Args:
            frame: BGR 格式的摄像头帧 (H, W, 3)

        Returns:
            (annotated_frame, gesture_result): 标注后的帧和手势识别结果
        """
        # BGR → RGB (MediaPipe 需要 RGB)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False

        results = self.hands.process(frame_rgb)

        frame_rgb.flags.writeable = True
        annotated = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

        gesture = GestureResult()

        if results.multi_hand_landmarks and results.multi_handedness:
            # 寻找左手
            left_hand_landmarks = self._find_left_hand(
                results.multi_hand_landmarks,
                results.multi_handedness,
            )

            if left_hand_landmarks is not None:
                gesture.hand_detected = True
                gesture = self._recognize_gestures(left_hand_landmarks, annotated.shape)

                # 绘制手部关键点
                self._draw_landmarks(annotated, left_hand_landmarks)

                # 绘制手势状态信息
                self._draw_status_overlay(annotated, gesture)

        # 冷却帧递减
        if self._jump_cooldown_counter > 0:
            self._jump_cooldown_counter -= 1

        return annotated, gesture

    def _find_left_hand(
        self,
        multi_hand_landmarks,
        multi_handedness,
    ) -> Optional[object]:
        """
        从多只手的结果中找到左手的关键点。

        MediaPipe 的 handedness 分类给出的是解剖学意义上的左右手，
        不受摄像头镜像影响。

        Returns:
            左手的关键点列表，如果未找到则返回 None
        """
        for idx, handedness in enumerate(multi_handedness):
            label = handedness.classification[0].label
            if label == "Left":
                return multi_hand_landmarks[idx]
        return None

    def _recognize_gestures(
        self,
        landmarks,
        frame_shape: Tuple[int, int, int],
    ) -> GestureResult:
        """
        从手部关键点识别手势。

        Args:
            landmarks: MediaPipe 手部关键点
            frame_shape: 帧的 (H, W, C)

        Returns:
            GestureResult 识别结果
        """
        h, w, _ = frame_shape
        result = GestureResult(hand_detected=True)

        # ----- 1. 拇指方向检测 -----
        thumb_mcp = landmarks.landmark[2]   # 拇指 MCP 关节
        thumb_tip = landmarks.landmark[4]   # 拇指指尖

        # 计算拇指尖相对 MCP 的水平偏移
        thumb_horizontal_offset = thumb_tip.x - thumb_mcp.x

        # 用手掌尺寸做归一化（手腕到中指 MCP 的距离）
        wrist = landmarks.landmark[0]
        middle_mcp = landmarks.landmark[9]
        hand_scale = max(abs(middle_mcp.x - wrist.x), abs(middle_mcp.y - wrist.y), 0.01)

        normalized_offset = thumb_horizontal_offset / hand_scale

        if normalized_offset < -self.THUMB_HORIZONTAL_THRESHOLD:
            result.move_direction = MoveDirection.LEFT
        elif normalized_offset > self.THUMB_HORIZONTAL_THRESHOLD:
            result.move_direction = MoveDirection.RIGHT
        else:
            result.move_direction = MoveDirection.NONE

        result.thumb_angle_deg = normalized_offset * 100  # 放大用于调试显示

        # ----- 2. 四指朝上检测 -----
        # 检查食指、中指、无名指、小指是否朝上
        # 判断标准：指尖 y < PIP关节 y（图像坐标系中 y 轴向下，所以更小的 y = 更高）
        fingers = [
            (8, 6),    # 食指: tip=8, PIP=6
            (12, 10),  # 中指: tip=12, PIP=10
            (16, 14),  # 无名指: tip=16, PIP=14
            (20, 18),  # 小指: tip=20, PIP=18
        ]

        fingers_up = 0
        for tip_idx, pip_idx in fingers:
            tip = landmarks.landmark[tip_idx]
            pip = landmarks.landmark[pip_idx]
            # y 值更小 = 位置更高（图像坐标）
            if tip.y < pip.y - self.FINGER_UP_THRESHOLD:
                fingers_up += 1

        result.fingers_up_count = fingers_up

        # 跳跃触发：四指朝上 + 未在冷却中
        if fingers_up >= self.MIN_FINGERS_UP_FOR_JUMP and self._jump_cooldown_counter == 0:
            result.is_jumping = True
            self._jump_cooldown_counter = self.JUMP_COOLDOWN_FRAMES

        return result

    def _draw_landmarks(self, frame: np.ndarray, landmarks) -> None:
        """在帧上绘制 MediaPipe 手部关键点和连线"""
        self.mp_draw.draw_landmarks(
            frame,
            landmarks,
            self.mp_hands.HAND_CONNECTIONS,
            self.mp_draw_styles.get_default_hand_landmarks_style(),
            self.mp_draw_styles.get_default_hand_connections_style(),
        )

    def _draw_status_overlay(self, frame: np.ndarray, gesture: GestureResult) -> None:
        """在帧上绘制手势识别状态文字"""
        h, w = frame.shape[:2]

        # 移动方向
        if gesture.move_direction == MoveDirection.LEFT:
            move_text = "MOVE: LEFT  <--"
            move_color = (0, 255, 255)  # 黄色
        elif gesture.move_direction == MoveDirection.RIGHT:
            move_text = "MOVE: RIGHT -->"
            move_color = (0, 255, 255)
        else:
            move_text = "MOVE: NONE"
            move_color = (128, 128, 128)

        cv2.putText(frame, move_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, move_color, 2)

        # 跳跃状态
        if gesture.is_jumping:
            jump_text = "JUMP! ^"
            jump_color = (0, 0, 255)  # 红色
        else:
            jump_text = f"Fingers up: {gesture.fingers_up_count}"
            jump_color = (128, 128, 128)

        cv2.putText(frame, jump_text, (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, jump_color, 2)

        # 手部检测状态
        status_text = "Left Hand: DETECTED"
        cv2.putText(frame, status_text, (10, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)

        # 操作提示
        hint_text = "Thumb=L/R | 4 Fingers Up=JUMP | Q=Quit"
        cv2.putText(frame, hint_text, (w - 500, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    def release(self):
        """释放 MediaPipe 资源"""
        self.hands.close()

    def reset_jump_cooldown(self):
        """重置跳跃冷却计数器"""
        self._jump_cooldown_counter = 0
