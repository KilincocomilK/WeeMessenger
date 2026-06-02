"""
微信消息发送器核心模块
负责 UI 自动化（查找窗口、文字/表情包发送）、队列调度和各子模块的协调。
"""

import logging
import random
import threading
import time
from queue import Queue, Empty
from typing import Any, Dict, Optional

import pyperclip
import uiautomation as auto

from .clipboard_utils import copy_file_to_clipboard
from .mouse_wanderer import MouseWanderer
from .voice_sender import VoiceSender, AUDIO_AVAILABLE
from .ws_client import WSCommandReceiver

logger = logging.getLogger("WeChatSender")


class WeChatSender:
    """
    微信消息发送器（WebSocket 控制版 · 全天候）

    组合鼠标漫游、WebSocket 指令接收、语音发送、剪贴板工具等模块，
    通过内部队列统一调度三种消息类型（文字、语音、表情包）
    """

    def __init__(self, config: dict = None, debug_mode: bool = False):
        if config is None:
            config = {}

        # 线程安全控制
        self.ui_lock = threading.Lock()
        self.send_queue: Queue[Dict[str, Any]] = Queue()
        self._stop_event = threading.Event()

        self.last_target: Optional[str] = None

        # ── 子模块初始化 ──

        # 鼠标漫游
        wanderer_cfg = config.get("wanderer", {})
        self.wanderer = MouseWanderer(
            min_interval=wanderer_cfg.get("min_interval", 10.0),
            max_interval=wanderer_cfg.get("max_interval", 30.0),
            wander_times_range=(
                wanderer_cfg.get("times_min", 1),
                wanderer_cfg.get("times_max", 3),
            ),
        )
        if not debug_mode and wanderer_cfg.get("enabled", True):
            self.wanderer.start()
        else:
            logger.info("[WCAC] 鼠标漫游已禁用")

        # 语音发送器（仅当音频可用）
        self.voice_sender: Optional[VoiceSender] = None
        if AUDIO_AVAILABLE:
            self.voice_sender = VoiceSender()

        # 发送工作线程
        self._worker_thread = threading.Thread(target=self._send_worker, daemon=True)
        self._worker_thread.start()

        # WebSocket 指令接收
        if not debug_mode:
            ws_url = config.get("ws_url")
            self.ws_receiver = WSCommandReceiver(ws_url, self.send_queue, self._stop_event)
            self.ws_receiver.start()
            logger.info(f"[WCAC] 微信发送器初始化完成！WebSocket 地址: {ws_url}")
        else:
            self.ws_receiver = None
            logger.info("[WCAC] 微信发送器初始化完成！（调试模式，跳过 WebSocket）")

    # ==================== 对外接口 ====================

    def send_message(self, target: str, message: str):
        """程序内直接调用，将文字消息投入发送队列"""
        self.send_queue.put({
            "type": "send_message",
            "target": target,
            "message": message,
        })

    # ==================== 发送工作线程 ====================

    def _send_worker(self):
        """发送工作线程主循环，从队列取指令并分发到对应处理方法"""
        logger.info("[WCAC] 发送工作线程启动！")
        with auto.UIAutomationInitializerInThread():
            while not self._stop_event.is_set():
                try:
                    cmd = self.send_queue.get(timeout=1)
                    cmd_type = cmd["type"]
                    target = cmd["target"]

                    if cmd_type == "send_message":
                        self._execute_send_message(target, cmd["message"])

                    elif cmd_type == "send_voice":
                        message = cmd.get("message", "")
                        # 若前置有文字消息，先发送文字
                        if message:
                            self._execute_send_message(target, message)
                            time.sleep(random.uniform(1.0, 2.0))
                        # 发送语音（若音频不可用则降级为仅文字）
                        if self.voice_sender:
                            self.voice_sender.send(
                                target,
                                cmd["voice_data"],
                                cmd["voice_format"],
                                ensure_chat_fn=self._ensure_chat_window,
                                lock=self.ui_lock,
                            )
                        else:
                            logger.warning("[WCAC] 音频不可用，语音发送已跳过")

                    elif cmd_type == "send_sticker":
                        self._execute_send_sticker(target, cmd["sticker_data"])

                    else:
                        logger.error(f"[WCAC] 未知指令类型: {cmd_type}")

                    # 指令间随机延迟
                    delay = random.randint(1, 3) + random.uniform(0.5, 1.5)
                    logger.info(f"[WCAC] 指令完成，等待 {delay:.1f} 秒")
                    time.sleep(delay)

                except Empty:
                    continue
                except Exception as e:
                    logger.error(f"[WCAC] 发送工作异常: {e}", exc_info=True)

    # ==================== UI 自动化（文字发送）====================

    @staticmethod
    def find_wechat_window() -> Optional[auto.WindowControl]:
        """查找微信主窗口"""
        window = auto.WindowControl(searchDepth=1, ClassName='WeChatMainWndForPC')
        if window.Exists(0, 0):
            return window
        window = auto.WindowControl(searchDepth=1, Name='微信')
        if window.Exists(0, 0):
            return window
        return None

    def _ensure_chat_window(self, target_name: str):
        """
        确保当前微信窗口已打开与 target_name 的聊天。
        若目标与上次相同则复用窗口，否则通过 Ctrl+F 搜索进入。
        """
        window = self.find_wechat_window()
        if not window:
            raise RuntimeError("[WCAC] 未找到微信窗口")
        window.SetActive()
        time.sleep(random.uniform(0.1, 0.3))

        if self.last_target == target_name:
            logger.info(f"[WCAC] 目标与上次相同 ({target_name})，复用当前聊天窗口")
            return

        logger.info(f"[WCAC] 搜索联系人 '{target_name}'")
        auto.SendKeys('{Ctrl}f')
        time.sleep(random.uniform(0.3, 0.5))
        pyperclip.copy(target_name)
        auto.SendKeys('{Ctrl}v')
        time.sleep(0.2)
        auto.SendKeys('{Enter}')
        time.sleep(random.uniform(0.8, 1.0))
        self.last_target = target_name

    def _execute_send_message(self, target: str, message: str):
        """
        执行文字消息的物理模拟发送：
        1. 查找并激活微信窗口
        2. 若目标与上次相同则快速粘贴发送；否则通过 Ctrl+F 搜索后发送
        """
        if not self.ui_lock.acquire(timeout=5.0):
            logger.error("[WCAC] 获取UI锁超时，取消发送")
            return

        try:
            time.sleep(random.uniform(0.5, 2.0))
            window = self.find_wechat_window()
            if not window:
                logger.error("[WCAC] 未找到微信窗口，发送中止")
                return
            window.SetActive()
            time.sleep(random.uniform(0.1, 0.3))

            fast_sent = False
            if self.last_target == target:
                logger.info(f"[WCAC] 目标与上次相同 ({target})，尝试快速发送")
                try:
                    pyperclip.copy(message)
                    time.sleep(random.uniform(0.1, 0.3))
                    auto.SendKeys('{Ctrl}v')
                    sleep_time = min(len(message) * 0.02, 2.0) + random.uniform(0.5, 1.5)
                    time.sleep(sleep_time)
                    auto.SendKeys('{Enter}')
                    logger.info(f"[WCAC] 快速发送完成: {target}")
                    fast_sent = True
                except Exception as e:
                    logger.warning(f"[WCAC] 快速发送失败: {e}")

            if not fast_sent:
                self._ensure_chat_window(target)

                # 粘贴消息并发送
                pyperclip.copy(message)
                time.sleep(random.uniform(0.3, 0.5))
                auto.SendKeys('{Ctrl}v')
                sleep_time = min(len(message) * 0.02, 2.0) + random.uniform(0.5, 1.5)
                time.sleep(sleep_time)
                auto.SendKeys('{Enter}')
                logger.info(f"[WCAC] 完整发送完成: {target}")

            self.last_target = target
            time.sleep(random.uniform(0.5, 1.5))

        except Exception as e:
            logger.error(f"[WCAC] 模拟发送文字异常: {e}", exc_info=True)
        finally:
            self.ui_lock.release()

    # ==================== 表情包发送 ====================

    def _execute_send_sticker(self, target: str, sticker_data_b64: str):
        """
        发送微信表情包（GIF）：
        1. 解码 base64 并保存为临时 .gif 文件
        2. 通过 CF_HDROP 将文件放入剪贴板
        3. 激活聊天窗口并粘贴发送
        """
        import base64
        import os
        import tempfile

        if not self.ui_lock.acquire(timeout=10.0):
            logger.error("[WCAC] 获取UI锁超时，取消表情包发送")
            return

        tmp_path = None
        try:
            sticker_bytes = base64.b64decode(sticker_data_b64)
            with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
                tmp_path = tmp.name
                tmp.write(sticker_bytes)

            logger.info(f"[WCAC] 表情包临时文件: {tmp_path}")

            self._ensure_chat_window(target)
            copy_file_to_clipboard(tmp_path)
            time.sleep(random.uniform(0.1, 0.3))

            auto.SendKeys('{Ctrl}v')
            time.sleep(random.uniform(1.0, 2.0))  # 等待微信加载预览
            auto.SendKeys('{Enter}')
            time.sleep(random.uniform(0.5, 1.0))

            logger.info(f"[WCAC] 表情包已发送给: {target}")

        except Exception as e:
            logger.error(f"[WCAC] 发送表情包异常: {e}", exc_info=True)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception as e:
                    logger.warning(f"[WCAC] 清理临时表情包文件失败: {e}")
            self.ui_lock.release()

    # ==================== 生命周期 ====================

    def shutdown(self):
        """安全关闭所有子模块和线程"""
        logger.info("[WCAC] 正在关闭微信发送器...")
        self._stop_event.set()
        if self.ws_receiver:
            self.ws_receiver.close()
            self.ws_receiver.join(timeout=3.0)
        self.wanderer.stop()
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=3.0)
        logger.info("[WCAC] 微信发送器已关闭！")
