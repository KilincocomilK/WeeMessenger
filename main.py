"""
微信消息发送器 — 程序入口
加载配置、初始化日志、启动全天候发送器并等待退出信号。
"""

import argparse
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


def debug_console_loop(sender):
    """调试控制台：交互式输入消息，发送到「文件传输助手」"""
    target = "文件传输助手"

    print()
    print("=" * 50)
    print("  WeeMessenger 调试控制台")
    print(f"  消息将发送到「{target}」")
    print("  输入 /quit 或 /exit 退出")
    print("  输入 /help  查看帮助")
    print("=" * 50)
    print()

    while True:
        try:
            line = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[WCAC] 收到退出信号")
            break

        if not line:
            continue

        if line in ("/quit", "/exit"):
            print("[WCAC] 退出调试模式")
            break

        if line == "/help":
            print()
            print("  可用命令:")
            print("    /quit, /exit    退出调试模式")
            print("    /help           显示此帮助信息")
            print(f"    任意其他文字      发送到「{target}」")
            print("    Ctrl+C          等同于 /quit")
            print()
            continue

        sender.send_message(target, line)
        print(f"[WCAC] 消息已投入发送队列 -> 「{target}」")


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="微信消息发送器")
    parser.add_argument("--debug", "-d", action="store_true",
                        help="调试模式：跳过 WebSocket，使用交互控制台发送测试消息")
    args = parser.parse_args()

    # 加载配置
    config = load_config()

    # 初始化日志 — 调试模式强制 DEBUG 级别
    log_level_str = "DEBUG" if args.debug else config.get("log_level", "INFO")
    log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # 启动发送器
    sender = WeChatSender(config, debug_mode=args.debug)

    if args.debug:
        print("[WCAC] 微信发送器已启动（调试模式），未连接 WebSocket")
        debug_console_loop(sender)
        sender.shutdown()
        print("[WCAC] 程序退出成功！拜拜！=w=")
    else:
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
