"""
剪贴板工具模块
提供 CF_HDROP 格式文件复制到剪贴板的功能，供表情包发送调用。
"""

import ctypes
import logging
import os

logger = logging.getLogger("WeChatSender.Clipboard")


class _DROPFILES(ctypes.Structure):
    """CF_HDROP 剪贴板格式所需的文件拖放结构"""
    _fields_ = [
        ("pFiles", ctypes.c_uint),   # 文件列表起始偏移
        ("pt",    ctypes.c_long * 2),  # 放置点坐标
        ("fNC",   ctypes.c_int),      # 是否非客户区
        ("fWide", ctypes.c_int),      # 1 表示 Unicode 字符
    ]


def copy_file_to_clipboard(file_path: str):
    """
    将文件以 CF_HDROP 格式放入剪贴板。
    微信能识别该格式，粘贴后可直接发送图片/文件。

    注意：成功调用后内存由剪贴板接管，调用方无需管理。
    """
    file_path = os.path.abspath(file_path)

    # 文件列表字符串（双 null 结尾）
    file_list = file_path + '\x00\x00'
    file_list_bytes = file_list.encode('utf-16-le')

    header_size = ctypes.sizeof(_DROPFILES)
    total_size = header_size + len(file_list_bytes)

    # 分配可移动全局内存
    GMEM_MOVEABLE = 0x0002
    hGlobal = ctypes.windll.kernel32.GlobalAlloc(GMEM_MOVEABLE, total_size)
    if not hGlobal:
        raise RuntimeError("GlobalAlloc 失败")

    try:
        locked_mem = ctypes.windll.kernel32.GlobalLock(hGlobal)
        if not locked_mem:
            raise RuntimeError("GlobalLock 失败")

        try:
            df = _DROPFILES()
            df.pFiles = header_size
            df.pt[0] = 0
            df.pt[1] = 0
            df.fNC = 0
            df.fWide = 1  # Unicode

            ctypes.memmove(locked_mem, ctypes.addressof(df), header_size)
            ctypes.memmove(locked_mem + header_size, file_list_bytes, len(file_list_bytes))
        finally:
            ctypes.windll.kernel32.GlobalUnlock(hGlobal)

        if not ctypes.windll.user32.OpenClipboard(None):
            raise RuntimeError("无法打开剪贴板")

        try:
            ctypes.windll.user32.EmptyClipboard()
            CF_HDROP = 15
            if not ctypes.windll.user32.SetClipboardData(CF_HDROP, hGlobal):
                raise RuntimeError("SetClipboardData 失败")
            hGlobal = None  # 内存已移交剪贴板，不再需要释放
        finally:
            ctypes.windll.user32.CloseClipboard()

    finally:
        if hGlobal:
            ctypes.windll.kernel32.GlobalFree(hGlobal)
