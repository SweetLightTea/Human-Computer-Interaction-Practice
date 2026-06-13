"""
手势检测模块 - Hand Detection & Gesture Recognition

使用 MediaPipe Hands 检测手部关键点，识别以下手势：

左手（移动/跳跃）:
  1. 左手大拇指方向 → 映射为水平移动方向 (左/右/静止)
  2. 左手四指朝上 → 映射为跳跃动作

右手（战斗/交互）:
  1. 右手握拳           → 鼠标左键（开火）
  2. 右手五指张开       → 鼠标右键（打开宝箱/捡宝石）
  3. 右手拇指朝上       → Q 键（装弹）

MediaPipe 手部关键点索引:
  0:  手腕 (Wrist)
  1:  拇指 CMC       2: 拇指 MCP      3: 拇指 IP      4: 拇指指尖
  5:  食指 MCP       6: 食指 PIP      7: 食指 DIP     8: 食指指尖
  9:  中指 MCP      10: 中指 PIP     11: 中指 DIP    12: 中指指尖
  13: 无名指 MCP    14: 无名指 PIP   15: 无名指 DIP  16: 无名指指尖
  17: 小指 MCP      18: 小指 PIP     19: 小指 DIP    20: 小指指尖
"""

import cv2
import mediapipe as mp
import numpy as np
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Tuple


class MoveDirection(Enum):
    """左手水平移动方向"""
    LEFT = auto()
    RIGHT = auto()
    NONE = auto()


class RightHandGesture(Enum):
    """右手手势类型"""
    NONE = auto()       # 未检测到 / 过渡状态
    FIST = auto()       # 握拳 → 鼠标左键（开火）
    OPEN_PALM = auto()  # 五指张开 → 鼠标右键（开宝箱/捡宝石）
    THUMB_UP = auto()   # 拇指朝上 → Q 键（装弹）


@dataclass
class GestureResult:
    """手势识别结果"""
    # 左手（移动/跳跃）
    move_direction: MoveDirection = MoveDirection.NONE
    is_jumping: bool = False
    left_hand_detected: bool = False
    thumb_angle_deg: float = 0.0
    fingers_up_count: int = 0

    # 右手（战斗/交互）
    right_hand_detected: bool = False
    right_hand_gesture: RightHandGesture = RightHandGesture.NONE
    # 兼容旧代码
    hand_detected: bool = False


class HandGestureDetector:
    """
    手部手势检测器

    使用 MediaPipe Hands 从摄像头画面中检测左右手，
    并识别预定义的手势动作。
    """

    # ---- 左手参数 ----
    THUMB_HORIZONTAL_THRESHOLD = 0.08
    FINGER_UP_THRESHOLD = 0.04
    MIN_FINGERS_UP_FOR_JUMP = 3
    JUMP_COOLDOWN_FRAMES = 10

    # ---- 右手参数 ----
    # 握拳：指尖到手腕的距离 < MCP到手腕的距离 × 此系数
    FIST_CURL_RATIO = 0.85
    # 张开：手指朝上阈值（同左手）
    OPEN_FINGER_UP_THRESHOLD = 0.03
    # 拇指朝上：拇指尖 y 需要远小于拇指 MCP y
    THUMB_UP_VERTICAL_THRESHOLD = 0.08
    # 拇指朝上时其他手指需要卷曲（指尖低于 PIP）
    THUMB_UP_CURL_THRESHOLD = 0.02

    def __init__(
        self,
        static_image_mode: bool = False,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
    ):
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

        # 右手手势防抖：连续 N 帧相同手势才确认
        self._right_gesture_history: list = []
        self._RIGHT_GESTURE_CONFIRM_FRAMES = 3

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, GestureResult]:
        """处理单帧画面"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False

        results = self.hands.process(frame_rgb)

        frame_rgb.flags.writeable = True
        annotated = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

        gesture = GestureResult()

        if results.multi_hand_landmarks and results.multi_handedness:
            # 分别处理左右手
            for idx, handedness in enumerate(results.multi_handedness):
                label = handedness.classification[0].label
                landmarks = results.multi_hand_landmarks[idx]

                if label == "Left":
                    gesture.left_hand_detected = True
                    gesture.hand_detected = True
                    gesture = self._recognize_left_gestures(gesture, landmarks, annotated.shape)
                    self._draw_landmarks(annotated, landmarks, (0, 255, 0))

                elif label == "Right":
                    gesture.right_hand_detected = True
                    gesture = self._recognize_right_gestures(gesture, landmarks, annotated.shape)
                    self._draw_landmarks(annotated, landmarks, (255, 165, 0))

        # 绘制状态信息（无论是否检测到手都显示）
        self._draw_status_overlay(annotated, gesture)

        # 冷却帧递减
        if self._jump_cooldown_counter > 0:
            self._jump_cooldown_counter -= 1

        return annotated, gesture

    # ================================================================
    #  左手手势识别（移动 + 跳跃）
    # ================================================================

    def _recognize_left_gestures(
        self,
        result: GestureResult,
        landmarks,
        frame_shape: Tuple[int, int, int],
    ) -> GestureResult:
        h, w, _ = frame_shape

        # ----- 拇指方向检测 -----
        thumb_mcp = landmarks.landmark[2]
        thumb_tip = landmarks.landmark[4]
        thumb_horizontal_offset = thumb_tip.x - thumb_mcp.x

        wrist = landmarks.landmark[0]
        middle_mcp = landmarks.landmark[9]
        hand_scale = max(abs(middle_mcp.x - wrist.x), abs(middle_mcp.y - wrist.y), 0.01)
        normalized_offset = thumb_horizontal_offset / hand_scale

        if normalized_offset < -self.THUMB_HORIZONTAL_THRESHOLD:
            result.move_direction = MoveDirection.LEFT
        elif normalized_offset > self.THUMB_HORIZONTAL_THRESHOLD:
            result.move_direction = MoveDirection.RIGHT

        result.thumb_angle_deg = normalized_offset * 100

        # ----- 四指朝上检测 -----
        fingers = [
            (8, 6), (12, 10), (16, 14), (20, 18),
        ]
        fingers_up = 0
        for tip_idx, pip_idx in fingers:
            tip = landmarks.landmark[tip_idx]
            pip = landmarks.landmark[pip_idx]
            if tip.y < pip.y - self.FINGER_UP_THRESHOLD:
                fingers_up += 1
        result.fingers_up_count = fingers_up

        if fingers_up >= self.MIN_FINGERS_UP_FOR_JUMP and self._jump_cooldown_counter == 0:
            result.is_jumping = True
            self._jump_cooldown_counter = self.JUMP_COOLDOWN_FRAMES

        return result

    # ================================================================
    #  右手手势识别（战斗/交互）
    # ================================================================

    def _recognize_right_gestures(
        self,
        result: GestureResult,
        landmarks,
        frame_shape: Tuple[int, int, int],
    ) -> GestureResult:
        """
        识别右手手势: FIST / OPEN_PALM / THUMB_UP

        判断逻辑：
          - 握拳: 所有手指卷曲（指尖低于 MCP）
          - 五指张开: 所有手指伸直（指尖高于 PIP）
          - 拇指朝上: 仅拇指伸直且朝上，其余手指卷曲
        """
        # 计算每根手指的伸直状态
        fingers_extended = self._get_fingers_extended(landmarks)

        # 拇指方向（专门用于 THUMB_UP 检测）
        thumb_tip = landmarks.landmark[4]
        thumb_mcp = landmarks.landmark[2]
        thumb_ip = landmarks.landmark[3]
        thumb_pointing_up = (thumb_mcp.y - thumb_tip.y) > self.THUMB_UP_VERTICAL_THRESHOLD

        # 其他四指卷曲状态
        index_curled = not fingers_extended[0]
        middle_curled = not fingers_extended[1]
        ring_curled = not fingers_extended[2]
        pinky_curled = not fingers_extended[3]
        thumb_extended = self._is_thumb_extended(landmarks)

        all_curled = index_curled and middle_curled and ring_curled and pinky_curled and (not thumb_extended)
        all_extended = all(fingers_extended) and thumb_extended

        # 判定手势
        if thumb_pointing_up and thumb_extended and index_curled and middle_curled and ring_curled and pinky_curled:
            detected = RightHandGesture.THUMB_UP
        elif all_extended:
            detected = RightHandGesture.OPEN_PALM
        elif all_curled:
            detected = RightHandGesture.FIST
        else:
            detected = RightHandGesture.NONE

        # 防抖：连续 N 帧相同手势才确认
        self._right_gesture_history.append(detected)
        if len(self._right_gesture_history) > self._RIGHT_GESTURE_CONFIRM_FRAMES:
            self._right_gesture_history.pop(0)

        if len(self._right_gesture_history) >= self._RIGHT_GESTURE_CONFIRM_FRAMES:
            if all(g == detected for g in self._right_gesture_history):
                result.right_hand_gesture = detected
            else:
                # 历史不一致，保持上一个已确认的手势
                result.right_hand_gesture = RightHandGesture.NONE

        return result

    def _get_fingers_extended(self, landmarks) -> list:
        """
        返回食指、中指、无名指、小指是否伸直的列表 [bool, bool, bool, bool]
        伸直标准：指尖 y < PIP关节 y（指尖在 PIP 上方）
        """
        fingers = [
            (8, 6),    # 食指 tip, PIP
            (12, 10),  # 中指 tip, PIP
            (16, 14),  # 无名指 tip, PIP
            (20, 18),  # 小指 tip, PIP
        ]
        extended = []
        for tip_idx, pip_idx in fingers:
            tip = landmarks.landmark[tip_idx]
            pip = landmarks.landmark[pip_idx]
            extended.append(tip.y < pip.y - self.OPEN_FINGER_UP_THRESHOLD)
        return extended

    def _is_thumb_extended(self, landmarks) -> bool:
        """
        判断拇指是否伸直。
        标准：拇指尖到手腕的距离 > 拇指MCP到手腕的距离
        """
        wrist = landmarks.landmark[0]
        thumb_tip = landmarks.landmark[4]
        thumb_mcp = landmarks.landmark[2]

        tip_dist = np.sqrt((thumb_tip.x - wrist.x)**2 + (thumb_tip.y - wrist.y)**2)
        mcp_dist = np.sqrt((thumb_mcp.x - wrist.x)**2 + (thumb_mcp.y - wrist.y)**2)

        return tip_dist > mcp_dist

    # ================================================================
    #  绘制
    # ================================================================

    def _draw_landmarks(self, frame: np.ndarray, landmarks, color: tuple) -> None:
        """在帧上绘制手部关键点和连线"""
        drawing_spec = self.mp_draw.DrawingSpec(color=color, thickness=2, circle_radius=3)
        connection_spec = self.mp_draw.DrawingSpec(color=color, thickness=2)
        self.mp_draw.draw_landmarks(
            frame, landmarks, self.mp_hands.HAND_CONNECTIONS,
            drawing_spec, connection_spec,
        )

    def _draw_status_overlay(self, frame: np.ndarray, gesture: GestureResult) -> None:
        """在帧上绘制手势识别状态文字"""
        h, w = frame.shape[:2]
        y_offset = 30

        # ---- 左手状态 ----
        if gesture.left_hand_detected:
            if gesture.move_direction == MoveDirection.LEFT:
                text, color = "L: MOVE LEFT  <--", (0, 255, 255)
            elif gesture.move_direction == MoveDirection.RIGHT:
                text, color = "L: MOVE RIGHT -->", (0, 255, 255)
            else:
                text, color = "L: MOVE NONE", (128, 128, 128)

            if gesture.is_jumping:
                text += " | JUMP! ^"
                color = (0, 0, 255)
        else:
            text, color = "L: NOT DETECTED", (100, 100, 100)

        cv2.putText(frame, text, (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        y_offset += 35

        # ---- 右手状态 ----
        if gesture.right_hand_detected:
            if gesture.right_hand_gesture == RightHandGesture.FIST:
                r_text, r_color = "R: FIST -> FIRE (LMB)", (0, 165, 255)
            elif gesture.right_hand_gesture == RightHandGesture.OPEN_PALM:
                r_text, r_color = "R: OPEN PALM -> INTERACT (RMB)", (0, 255, 127)
            elif gesture.right_hand_gesture == RightHandGesture.THUMB_UP:
                r_text, r_color = "R: THUMB UP -> RELOAD (Q)", (255, 255, 0)
            else:
                r_text, r_color = "R: (transition...)", (128, 128, 128)
        else:
            r_text, r_color = "R: NOT DETECTED", (100, 100, 100)

        cv2.putText(frame, r_text, (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, r_color, 2)

        # 底部操作提示
        hint_text = "L:Thumb=L/R 4Fingers=JUMP | R:Fist=FIRE Open=INTERACT ThumbUp=RELOAD | Q=Quit"
        cv2.putText(frame, hint_text, (10, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    def release(self):
        """释放 MediaPipe 资源"""
        self.hands.close()

    def reset_jump_cooldown(self):
        """重置跳跃冷却计数器"""
        self._jump_cooldown_counter = 0
