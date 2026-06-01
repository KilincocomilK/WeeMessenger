"""
WebSocket 客户端模块
连接 WebSocket 服务器，接收发送指令（文字/语音/表情包），校验后投递到共享队列。
"""

import json
import logging
import threading
import time
from queue import Queue
from typing import Any, Dict, Optional

import websocket

logger = logging.getLogger("WeChatSender.WSClient")


class WSCommandReceiver:
    """WebSocket 指令接收器，负责连接/重连和消息校验"""

    def __init__(self, ws_url: str, send_queue: Queue, stop_event: threading.Event):
        self.ws_url = ws_url
        self.send_queue = send_queue
        self._stop_event = stop_event
        self.ws: Optional[websocket.WebSocketApp] = None
        self.connected = False
        self._thread = threading.Thread(target=self._connect_loop, daemon=True)

    def start(self):
        """启动 WebSocket 连接线程"""
        self._thread.start()

    def _connect_loop(self):
        """WebSocket 重连循环，断线后每 5 秒尝试重连"""
        while not self._stop_event.is_set():
            try:
                self.ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self.ws.run_forever()
            except Exception as e:
                logger.error(f"[WCAC] WebSocket 连接异常: {e}")
            self._stop_event.wait(5)

    def _on_open(self, ws):
        self.connected = True
        logger.info("WebSocket 已连接")

    def _on_error(self, ws, error):
        logger.error(f"[WCAC] WebSocket 错误: {error}")
        self.connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info("[WCAC] WebSocket 连接关闭")
        self.connected = False

    def _on_message(self, ws, message):
        """接收 JSON 指令，校验字段后投入发送队列"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            target = data.get("target")
            if not target:
                logger.warning("[WCAC] 收到的指令缺少 target 字段，忽略")
                return

            if msg_type == "send_message":
                content = data.get("message")
                if not content:
                    logger.warning("[WCAC] send_message 缺少 message 字段，忽略")
                    return
                self.send_queue.put({
                    "type": "send_message",
                    "target": target,
                    "message": content,
                })
                logger.info(f"[WCAC] 接收 send_message: 目标='{target}', 长度={len(content)}")

            elif msg_type == "send_voice":
                voice_data_b64 = data.get("voice_data")
                if not voice_data_b64:
                    logger.warning("[WCAC] send_voice 缺少 voice_data，将只发送文字")
                    content = data.get("message")
                    if content:
                        self.send_queue.put({
                            "type": "send_message",
                            "target": target,
                            "message": content,
                        })
                    return

                self.send_queue.put({
                    "type": "send_voice",
                    "target": target,
                    "message": data.get("message", ""),
                    "voice_data": voice_data_b64,
                    "voice_format": data.get("format", "mp3"),
                })
                logger.info(f"[WCAC] 接收 send_voice: 目标='{target}', 音频长度={len(voice_data_b64)}")

            elif msg_type == "send_sticker":
                sticker_data_b64 = data.get("sticker_data")
                if not sticker_data_b64:
                    logger.warning("[WCAC] send_sticker 缺少 sticker_data 字段，忽略")
                    return
                self.send_queue.put({
                    "type": "send_sticker",
                    "target": target,
                    "sticker_data": sticker_data_b64,
                })
                logger.info(f"[WCAC] 接收 send_sticker: 目标='{target}', 数据长度={len(sticker_data_b64)}")

            else:
                logger.debug(f"[WCAC] 忽略未知指令类型: {msg_type}")

        except json.JSONDecodeError:
            logger.error(f"[WCAC] WebSocket 消息不是有效的 JSON: {message}")
        except Exception as e:
            logger.error(f"[WCAC] 处理 WebSocket 消息异常: {e}", exc_info=True)

    def close(self):
        """关闭 WebSocket 连接"""
        if self.ws:
            self.ws.close()

    def join(self, timeout: float = 3.0):
        """等待 WebSocket 线程退出"""
        if self._thread.is_alive():
            self._thread.join(timeout=timeout)
