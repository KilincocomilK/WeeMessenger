"""
共享消息校验模块
从原始 JSON 数据中提取、校验并标准化为 send_queue 所需的命令字典。
WebSocket 和 HTTP 接收器共用此函数。
"""

from typing import Any, Dict, Optional, Tuple


def validate_and_normalize_message(data: Any) -> Tuple[Optional[Dict], Optional[str]]:
    """
    校验并标准化上游消息。

    Returns:
        (normalized_dict, None) — 校验通过，dict 可直接投入 send_queue
        (None, error_message)    — 校验失败，error_message 为中文错误描述
    """
    if not isinstance(data, dict):
        return None, "消息必须是 JSON 对象"

    msg_type = data.get("type")
    target = data.get("target")

    if not target:
        return None, "缺少 target 字段"

    if msg_type == "send_message":
        content = data.get("message")
        if not content:
            return None, "send_message 缺少 message 字段"
        return {"type": "send_message", "target": target, "message": content}, None

    elif msg_type == "send_voice":
        voice_data_b64 = data.get("voice_data")
        if not voice_data_b64:
            content = data.get("message")
            if content:
                return {
                    "type": "send_message",
                    "target": target,
                    "message": content,
                }, None
            return None, "send_voice 缺少 voice_data 字段"

        voice_format = data.get("voice_format") or data.get("format") or "mp3"
        return {
            "type": "send_voice",
            "target": target,
            "message": data.get("message", ""),
            "voice_data": voice_data_b64,
            "voice_format": voice_format,
        }, None

    elif msg_type == "send_sticker":
        sticker_data_b64 = data.get("sticker_data")
        if not sticker_data_b64:
            return None, "send_sticker 缺少 sticker_data 字段"
        return {
            "type": "send_sticker",
            "target": target,
            "sticker_data": sticker_data_b64,
        }, None

    return None, f"未知指令类型: {msg_type}"
