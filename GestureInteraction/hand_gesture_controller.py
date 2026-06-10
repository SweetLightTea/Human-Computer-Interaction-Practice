"""
手势交互控制器 - Hand Gesture Controller (主入口)

通过摄像头检测左手手势，将其映射为游戏键盘输入。

============================================================
  手势映射关系 (Gesture → Game Input)
============================================================
  左手大拇指指向左侧   →  按住 A 键 (角色向左移动)
  左手大拇指指向右侧   →  按住 D 键 (角色向右移动)
  左手大拇指居中       →  释放 A/D 键 (角色停止)
  左手四指朝上         →  点按 Space 键 (角色跳跃)
============================================================
  对应 Unity 代码中的输入:
    PlayerState.cs:       Input.GetAxisRaw("Horizontal")
    PlayerGroundState.cs: Input.GetKeyDown(KeyCode.Space)
============================================================

使用方式:
  1. 安装依赖: pip install -r requirements.txt
  2. 运行本脚本: python hand_gesture_controller.py
  3. 将左手对准摄像头，比划手势控制游戏
  4. 按 Q 键退出程序

注意事项:
  - 推荐在光线充足的环境下使用
  - 左手应完整出现在摄像头画面中
  - 摄像头画面已做镜像处理，操作直觉化
  - 本程序不会修改任何 Unity 项目文件
"""

import cv2
import sys
import signal
import argparse
from typing import Optional

from gesture_detector import HandGestureDetector, GestureResult, MoveDirection
from input_mapper import InputMapper


# ============================================================
#  配置常量
# ============================================================

DEFAULT_CAMERA_ID = 0
WINDOW_NAME = "Gesture Controller - Left Hand (Q=Quit, M=Mirror Toggle)"
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30


class GestureController:
    """
    手势交互主控制器

    负责:
      1. 打开摄像头捕获画面
      2. 逐帧检测左手手势
      3. 将手势映射为键盘输入
      4. 显示实时预览画面
    """

    def __init__(
        self,
        camera_id: int = DEFAULT_CAMERA_ID,
        flip_horizontal: bool = True,
        show_preview: bool = True,
        verbose: bool = False,
    ):
        """
        Args:
            camera_id: 摄像头设备 ID（默认 0）
            flip_horizontal: 是否水平镜像画面（推荐开启，操作直觉化）
            show_preview: 是否显示预览窗口
            verbose: 是否打印详细日志
        """
        self.camera_id = camera_id
        self.flip_horizontal = flip_horizontal
        self.show_preview = show_preview
        self.verbose = verbose

        # 初始化组件
        self.detector: Optional[HandGestureDetector] = None
        self.mapper: Optional[InputMapper] = None
        self.capture: Optional[cv2.VideoCapture] = None

        # 运行状态
        self._running = False
        self._frame_count = 0
        self._fps = 0.0

    # ---- 生命周期 ----

    def start(self) -> None:
        """启动手势控制器"""
        print("=" * 60)
        print("  手势交互控制器 - Hand Gesture Controller")
        print("=" * 60)
        print()
        print("[INFO] 正在初始化...")

        # 初始化手势检测器
        self.detector = HandGestureDetector(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
        )
        print("[INFO] MediaPipe 手势检测器已加载")

        # 初始化键盘映射器
        self.mapper = InputMapper(use_direct_input=True)
        print(f"[INFO] 键盘映射器已加载 (后端: {self.mapper._backend})")

        # 打开摄像头
        self.capture = cv2.VideoCapture(self.camera_id)
        if not self.capture.isOpened():
            raise RuntimeError(f"无法打开摄像头 (ID={self.camera_id})")

        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.capture.set(cv2.CAP_PROP_FPS, TARGET_FPS)
        print(f"[INFO] 摄像头已打开 (ID={self.camera_id})")
        print()

        self._print_guide()
        print()

        # 创建置顶预览窗口（即使在 Unity 前台运行时也不会被遮挡）
        if self.show_preview:
            cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(WINDOW_NAME, FRAME_WIDTH, FRAME_HEIGHT)
            cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # 主循环
        self._running = True
        self._run_loop()

    def stop(self) -> None:
        """停止手势控制器并释放资源"""
        print("\n[INFO] 正在关闭...")
        self._running = False

        # 释放所有按键
        if self.mapper:
            self.mapper.release_all()
            print("[INFO] 已释放所有按键")

        # 释放 MediaPipe
        if self.detector:
            self.detector.release()
            print("[INFO] MediaPipe 已释放")

        # 关闭摄像头
        if self.capture and self.capture.isOpened():
            self.capture.release()
            print("[INFO] 摄像头已释放")

        # 关闭窗口
        cv2.destroyAllWindows()
        print("[INFO] 手势控制器已安全退出")

    # ---- 主循环 ----

    def _run_loop(self) -> None:
        """手势识别主循环"""
        import time

        prev_time = time.time()
        fps_update_interval = 0.5  # 每 0.5 秒更新一次 FPS 显示
        prev_gesture: Optional[GestureResult] = None

        while self._running:
            # 读取摄像头帧
            ret, frame = self.capture.read()
            if not ret:
                print("[WARN] 无法读取摄像头帧，重试中...")
                continue

            self._frame_count += 1

            # 水平镜像（让操作更直觉化）
            if self.flip_horizontal:
                frame = cv2.flip(frame, 1)

            # 手势检测
            annotated_frame, gesture = self.detector.process_frame(frame)

            # 映射到键盘输入
            self.mapper.apply_gesture(gesture)

            # 详细日志（手势状态变化时）
            if self.verbose and gesture != prev_gesture:
                self._log_gesture_change(gesture)

            prev_gesture = gesture

            # 更新 FPS
            now = time.time()
            elapsed = now - prev_time
            if elapsed >= fps_update_interval:
                self._fps = self._frame_count / elapsed
                self._frame_count = 0
                prev_time = now

            # 在画面上叠加 FPS
            cv2.putText(
                annotated_frame, f"FPS: {self._fps:.1f}",
                (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1,
            )

            # 显示预览窗口
            if self.show_preview:
                cv2.imshow(WINDOW_NAME, annotated_frame)

            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("[INFO] 用户按下 Q 键，退出...")
                break
            elif key == ord('m'):
                self.flip_horizontal = not self.flip_horizontal
                print(f"[INFO] 镜像模式: {'开启' if self.flip_horizontal else '关闭'}")
            elif key == ord('v'):
                self.verbose = not self.verbose
                print(f"[INFO] 详细日志: {'开启' if self.verbose else '关闭'}")
            elif key == ord('r'):
                self.detector.reset_jump_cooldown()
                print("[INFO] 跳跃冷却已重置")

    # ---- 辅助方法 ----

    def _print_guide(self) -> None:
        """打印操作指南"""
        print("-" * 44)
        print("  操作指南:")
        print()
        print("  左手大拇指 ←  →  A 键 (左移)")
        print("  左手大拇指 →  →  D 键 (右移)")
        print("  左手四指朝上  →  Space 键 (跳跃)")
        print()
        print("  键盘控制:")
        print("    Q - 退出")
        print("    M - 切换镜像模式")
        print("    V - 切换详细日志")
        print("    R - 重置跳跃冷却")
        print("-" * 44)
        print()
        print("[READY] 手势控制器已就绪，请确保 Unity 游戏窗口处于活动状态")
        print("[READY] 将左手对准摄像头开始控制...")

    def _log_gesture_change(self, gesture: GestureResult) -> None:
        """记录手势状态变化"""
        parts = []

        if not gesture.hand_detected:
            parts.append("[GESTURE] 未检测到左手")
        else:
            if gesture.move_direction == MoveDirection.LEFT:
                parts.append("移动: ← 左")
            elif gesture.move_direction == MoveDirection.RIGHT:
                parts.append("移动: → 右")
            else:
                parts.append("移动: · 停")

            if gesture.is_jumping:
                parts.append("跳跃: ↑")

            parts.append(f"(拇指偏角:{gesture.thumb_angle_deg:.1f} 朝上手指:{gesture.fingers_up_count})")

        print(" | ".join(parts))

    def _signal_handler(self, signum, frame) -> None:
        """处理 SIGINT/SIGTERM 信号，确保安全退出"""
        print(f"\n[INFO] 收到信号 {signum}，正在安全退出...")
        self.stop()
        sys.exit(0)


# ============================================================
#  命令行入口
# ============================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="手势交互控制器 - 通过摄像头手势控制 2D 横板游戏",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python hand_gesture_controller.py                    # 使用默认摄像头
  python hand_gesture_controller.py --camera 1         # 使用第二个摄像头
  python hand_gesture_controller.py --no-preview       # 不显示预览窗口
  python hand_gesture_controller.py --verbose          # 打印详细日志
  python hand_gesture_controller.py --no-flip          # 关闭镜像
        """,
    )
    parser.add_argument(
        "-c", "--camera", type=int, default=DEFAULT_CAMERA_ID,
        help=f"摄像头设备 ID (默认: {DEFAULT_CAMERA_ID})",
    )
    parser.add_argument(
        "--no-preview", action="store_true",
        help="不显示预览窗口（减少性能开销）",
    )
    parser.add_argument(
        "--no-flip", action="store_true",
        help="关闭水平镜像",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="打印详细日志",
    )
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    controller = GestureController(
        camera_id=args.camera,
        flip_horizontal=not args.no_flip,
        show_preview=not args.no_preview,
        verbose=args.verbose,
    )

    try:
        controller.start()
    except KeyboardInterrupt:
        pass  # 已在 signal handler 中处理
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1
    finally:
        controller.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
