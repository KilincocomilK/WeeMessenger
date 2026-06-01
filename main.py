"""
微信消息发送器 — 程序入口
加载配置、初始化日志、启动全天候发送器并等待退出信号。
"""

import ctypes
import logging
import sys
import time

from src.config import load_config
from src.wechat_sender import WeChatSender

# 启用 DPI 感知（避免在高分屏上 UI 自动化坐标偏移）
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


def main():
    # 加载配置
    config = load_config()

    # 初始化日志
    log_level = getattr(logging, config.get("log_level", "INFO"), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # 启动全天候发送器
    sender = WeChatSender(config)
    print("[WCAC] 微信发送器已启动（全天候），等待 WebSocket 指令...")
    print("[WCAC] 按 Ctrl+C 退出")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[WCAC] 收到退出信号")
    finally:
        sender.shutdown()
        print("[WCAC] 程序退出成功！拜拜！=w=")


if __name__ == "__main__":
    main()
