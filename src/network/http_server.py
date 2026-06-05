"""
HTTP 服务器模块
监听 HTTP POST 请求，接收与 WebSocket 相同格式的 JSON 指令，校验后投递到共享队列。
与 WebSocket 模式可并行运行。
"""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from queue import Queue
from socketserver import ThreadingMixIn
from typing import Optional

from .message_validator import validate_and_normalize_message

logger = logging.getLogger("WeChatSender.HTTPServer")


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """多线程 HTTP 服务器，请求在独立线程中处理，关闭时不阻塞。"""
    daemon_threads = True


class _CommandRequestHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器，将 POST JSON 指令校验后投入 send_queue。"""

    # 类级属性，由 HTTPCommandReceiver 在启动前注入
    send_queue: Queue = None  # type: ignore[assignment]
    stop_event: threading.Event = None  # type: ignore[assignment]

    def _send_json(self, code: int, body: dict):
        """发送 JSON 响应，自动设置 Content-Type 和长度。"""
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_HEAD(self):
        """HEAD /health 返回空体健康检查"""
        if self.path in ("/health", "/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        """GET /health 健康检查"""
        if self.path in ("/health", "/"):
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"status": "error", "message": "Not found"})

    def do_POST(self):
        """POST / 和 POST /api/message 接收 JSON 指令"""
        if self.path not in ("/", "/api/message"):
            self._send_json(404, {"status": "error", "message": "Not found"})
            return

        # 读取请求体
        content_length = self.headers.get("Content-Length")
        if not content_length or int(content_length) == 0:
            self._send_json(400, {"status": "error", "message": "请求体为空"})
            return

        try:
            raw = self.rfile.read(int(content_length))
        except Exception:
            self._send_json(400, {"status": "error", "message": "读取请求体失败"})
            return

        # UTF-8 解码
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            self._send_json(400, {"status": "error", "message": "请求体必须是 UTF-8 编码"})
            return

        # JSON 解析
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            self._send_json(400, {"status": "error", "message": f"JSON 解析失败: {e}"})
            return

        # 消息校验与投递
        cmd, error = validate_and_normalize_message(data)
        if error:
            self._send_json(400, {"status": "error", "message": error})
            return

        self.send_queue.put(cmd)
        cmd_type = cmd["type"]
        target = cmd["target"]

        if cmd_type == "send_message":
            detail = f"目标='{target}', 长度={len(cmd['message'])}"
        elif cmd_type == "send_voice":
            detail = f"目标='{target}', 音频长度={len(cmd['voice_data'])}"
        elif cmd_type == "send_sticker":
            detail = f"目标='{target}', 数据长度={len(cmd['sticker_data'])}"
        else:
            detail = ""

        logger.info(f"[WeeMessenger - 提示] HTTP 接收 {cmd_type}: {detail}")
        self._send_json(200, {"status": "ok", "type": cmd_type})

    def log_message(self, fmt, *args):
        """将 http.server 默认日志转发到项目 logger"""
        logger.debug(f"[HTTP] {fmt % args}")


class HTTPCommandReceiver:
    """HTTP 指令接收器，在独立线程中运行 HTTP 服务器"""

    def __init__(self, host: str, port: int, send_queue: Queue, stop_event: threading.Event):
        self.host = host
        self.port = port
        self.send_queue = send_queue
        self._stop_event = stop_event
        self._httpd: Optional[_ThreadingHTTPServer] = None
        self._thread = threading.Thread(target=self._run_server, daemon=True)

    def start(self):
        """启动 HTTP 服务器线程"""
        self._thread.start()

    def _run_server(self):
        """HTTP 服务器主循环"""
        # 注入队列到请求处理器
        _CommandRequestHandler.send_queue = self.send_queue
        _CommandRequestHandler.stop_event = self._stop_event

        try:
            self._httpd = _ThreadingHTTPServer((self.host, self.port), _CommandRequestHandler)
            logger.info(
                f"[WeeMessenger - 提示] HTTP 服务器已启动: http://{self.host}:{self.port}"
            )
            self._httpd.serve_forever()
        except OSError as e:
            logger.error(f"[WeeMessenger - 错误] HTTP 服务器启动失败 ({self.host}:{self.port}): {e}")
        except Exception as e:
            logger.error(f"[WeeMessenger - 错误] HTTP 服务器异常: {e}", exc_info=True)

    def close(self):
        """关闭 HTTP 服务器"""
        if self._httpd:
            try:
                self._httpd.shutdown()
            except Exception:
                pass
            try:
                self._httpd.server_close()
            except Exception:
                pass

    def join(self, timeout: float = 3.0):
        """等待 HTTP 服务器线程退出"""
        if self._thread.is_alive():
            self._thread.join(timeout=timeout)
