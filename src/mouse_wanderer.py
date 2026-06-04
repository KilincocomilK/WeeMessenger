"""
鼠标自然漫游模块
在屏幕范围内随机移动鼠标，模拟真人不定期操作，避免被检测为机器人。
"""

import ctypes
import logging
import math
import random
import threading
import time
from typing import Optional

import uiautomation as auto

logger = logging.getLogger("WeChatSender.MouseWanderer")


class MouseWanderer:
    """独立的鼠标漫游器，在后台线程中定时随机移动鼠标"""

    def __init__(
        self,
        min_interval: float = 10.0,
        max_interval: float = 30.0,
        wander_times_range: tuple = (1, 3),
    ):
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.wander_times_range = wander_times_range
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @staticmethod
    def _human_mouse_move(start_x: int, start_y: int, end_x: int, end_y: int):
        """模拟带有随机加速度和偏角的真人化鼠标移动轨迹"""
        steps = random.randint(3, 12)
        weights = [random.random() for _ in range(steps)]
        total_weight = sum(weights)
        ratios = [w / total_weight for w in weights]

        dx = end_x - start_x
        dy = end_y - start_y
        cur_x, cur_y = start_x, start_y
        points = []

        for ratio in ratios:
            step_dx = dx * ratio
            step_dy = dy * ratio
            # 添加随机偏角（±20度）
            angle = random.uniform(-0.349, 0.349)
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            offset_x = step_dx * cos_a - step_dy * sin_a
            offset_y = step_dx * sin_a + step_dy * cos_a
            new_x = cur_x + offset_x
            new_y = cur_y + offset_y
            screen_width = ctypes.windll.user32.GetSystemMetrics(0)
            screen_height = ctypes.windll.user32.GetSystemMetrics(1)
            new_x = max(0, min(int(new_x), screen_width))
            new_y = max(0, min(int(new_y), screen_height))
            points.append((new_x, new_y))
            cur_x, cur_y = new_x, new_y

        # 终点精确对齐目标位置
        points[-1] = (end_x, end_y)

        for px, py in points:
            auto.SetCursorPos(int(px), int(py))
            time.sleep(random.uniform(0.001, 0.1))

    def _random_wander(self, times: int = 1):
        """在屏幕范围内随机移动鼠标若干次"""
        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)
        for _ in range(times):
            end_x = random.randint(50, screen_width - 50)
            end_y = random.randint(50, screen_height - 50)
            start_x, start_y = auto.GetCursorPos()
            # 若目标太近则重新选取
            if abs(start_x - end_x) < 100 and abs(start_y - end_y) < 100:
                end_x = random.randint(0, screen_width)
                end_y = random.randint(0, screen_height)
            self._human_mouse_move(start_x, start_y, end_x, end_y)
            time.sleep(random.uniform(0.2, 1.5))

    def _run_loop(self):
        """鼠标漫游主循环（在独立线程中运行）"""
        logger.info("[WeeMessenger - 提示] 鼠标漫游线程已启动")
        with auto.UIAutomationInitializerInThread():
            while not self._stop_event.is_set():
                # 使用 Event.wait 替代 time.sleep，关闭时可即时响应
                self._stop_event.wait(random.uniform(self.min_interval, self.max_interval))
                if self._stop_event.is_set():
                    break
                times = random.randint(*self.wander_times_range)
                try:
                    self._random_wander(times)
                except Exception as e:
                    logger.warning(f"[WeeMessenger - 警告] 鼠标漫游异常: {e}")

    def start(self):
        """启动鼠标漫游后台线程"""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止鼠标漫游线程"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
