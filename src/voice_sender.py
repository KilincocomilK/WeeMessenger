"""
语音消息发送模块
将 base64 编码的音频解码播放，同时模拟 Alt 按键以触发微信语音输入。
"""

import base64
import ctypes
import logging
import os
import tempfile
import threading
import time

logger = logging.getLogger("WeChatSender.Voice")

# 初始化 pygame.mixer（音频播放后端，同时用于获取音频时长）
AUDIO_AVAILABLE = False
try:
    import pygame.mixer
    pygame.mixer.init()
    AUDIO_AVAILABLE = True
    logger.info("[WeeMessenger - 提示] 音频播放后端：pygame.mixer")
except Exception as e:
    logger.warning(f"[WeeMessenger - 警告] pygame.mixer 初始化失败: {e}。语音功能不可用。")


# ── SendInput 键盘模拟结构 ──
# 必须使用联合体（union）匹配 Windows INPUT 结构体大小，否则 SendInput 静默失败

class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         ctypes.c_ushort),
        ("wScan",       ctypes.c_ushort),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          ctypes.c_long),
        ("dy",          ctypes.c_long),
        ("mouseData",   ctypes.c_ulong),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg",    ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", _MOUSEINPUT),
        ("ki", _KEYBDINPUT),
        ("hi", _HARDWAREINPUT),
    ]


class _INPUT(ctypes.Structure):
    _fields_ = [
        ("type",  ctypes.c_ulong),
        ("union", _INPUT_UNION),
    ]


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_MENU = 0x12


def _send_key(vk_code: int, key_up: bool = False):
    """通过 SendInput 发送单个键盘事件"""
    flags = KEYEVENTF_KEYUP if key_up else 0
    inp = _INPUT(
        type=INPUT_KEYBOARD,
        union=_INPUT_UNION(ki=_KEYBDINPUT(
            wVk=vk_code, wScan=0, dwFlags=flags, time=0, dwExtraInfo=0,
        )),
    )
    sent = ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))
    if sent != 1:
        logger.warning(f"[WeeMessenger - 警告] SendInput 返回 {sent}，按键模拟可能未生效")


def _safe_alt_hold(hold_seconds: float):
    """
    模拟按住 Alt 键指定时长，然后安全释放。
    使用 try/finally 确保即使异常发生也会释放 Alt，避免键盘卡死。
    """
    _send_key(VK_MENU, key_up=False)
    logger.info(f"[WeeMessenger - 提示] 已按下 Alt 键，持续 {hold_seconds:.1f}s ……")
    try:
        time.sleep(hold_seconds)
    finally:
        _send_key(VK_MENU, key_up=True)
        logger.info("[WeeMessenger - 提示] 已释放 Alt 键")


class VoiceSender:
    """语音消息发送器，负责音频解码、播放和微信语音输入模拟"""

    def send(self, target_name: str, voice_data_b64: str, voice_format: str = "mp3",
             ensure_chat_fn=None, lock: threading.Lock = None):
        """
        发送语音消息：
        1. 解码 base64 音频 → 临时文件
        2. 确保聊天窗口已就绪（持有 UI 锁）
        3. 播放音频同时按住 Alt 键（微信语音输入快捷键）
        4. 释放 Alt 键完成发送
        """
        if not AUDIO_AVAILABLE:
            logger.error("[WeeMessenger - 错误] 音频库不可用，无法发送语音")
            return

        tmp_path = None

        # 获取 UI 锁（如果有），保护 ensure_chat_fn 及 Alt 按键操作
        if lock:
            if not lock.acquire(timeout=10.0):
                logger.error("[WeeMessenger - 错误] 获取UI锁超时，取消语音发送")
                return

        try:
            # 解码音频并保存为临时文件
            audio_bytes = base64.b64decode(voice_data_b64)
            with tempfile.NamedTemporaryFile(suffix=f".{voice_format}", delete=False) as tmp:
                tmp_path = tmp.name
                tmp.write(audio_bytes)

            logger.info(f"[WeeMessenger - 提示] 语音文件已临时保存: {tmp_path}")

            # 确保聊天窗口就绪（在锁保护下执行）
            if ensure_chat_fn:
                ensure_chat_fn(target_name)

            # 通过 pygame 加载音频并获取时长
            sound = pygame.mixer.Sound(tmp_path)
            duration = max(sound.get_length(), 0.0)
            logger.info(f"[WeeMessenger - 提示] 音频时长: {duration:.2f} 秒")

            # 使用 pygame 播放音频
            play_thread = threading.Thread(target=sound.play, daemon=True)
            play_thread.start()

            # 微信要求录音至少 2 秒，不足则延长 Alt 按住时间
            MIN_VOICE_DURATION = 2.0
            hold_duration = max(duration, MIN_VOICE_DURATION)
            if hold_duration > duration:
                logger.info(
                    f"[WeeMessenger - 提示] 音频时长 {duration:.2f}s 不足 {MIN_VOICE_DURATION}s，"
                    f"[WeeMessenger - 提示] Alt 按住时间延长至 {hold_duration:.2f}s"
                )

            # 安全模拟 Alt 按住（异常时自动释放）
            _safe_alt_hold(hold_duration)
            play_thread.join(timeout=hold_duration + 2.0)
            logger.info(f"[WeeMessenger - 提示] 语音消息已发送给: {target_name}")

        except Exception as e:
            logger.error(f"[WeeMessenger - 错误] 发送语音异常: {e}", exc_info=True)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception as e:
                    logger.warning(f"[WeeMessenger - 警告] 清理临时语音文件失败: {e}")
            if lock:
                lock.release()
