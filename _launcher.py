"""WeeMessenger 启动器 — 管理环境、依赖、菜单和程序启动"""
import atexit
import logging
import msvcrt
import os
import signal
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
PID_FILE = os.path.join(BASE_DIR, ".wee_pid")

# Windows 控制台设为 UTF-8 编码
if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetConsoleOutputCP(65001)

# 日志配置
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler])
logger = logging.getLogger("WeeMessenger.Launcher")

# 子进程管理
_child_proc = None


def _kill_child():
    """强制终止子进程（如果还在运行）"""
    global _child_proc
    if _child_proc is not None and _child_proc.poll() is None:
        _child_proc.kill()
        _child_proc.wait(timeout=10)


def _cleanup_stale_instance():
    """清理上一次残留的 main.py 进程"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                old_pid = int(f.read().strip())
            try:
                os.kill(old_pid, signal.SIGTERM)
            except OSError:
                pass  # 进程已不存在
        except (ValueError, OSError):
            pass
        finally:
            try:
                os.unlink(PID_FILE)
            except OSError:
                pass


def _save_child_pid(pid):
    """保存子进程 PID，供下次启动时清理残留"""
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(pid))
    except OSError:
        pass


def _remove_pid_file():
    try:
        if os.path.exists(PID_FILE):
            os.unlink(PID_FILE)
    except OSError:
        pass


# 注册控制台事件处理 — 覆盖窗口关闭按钮（CTRL_CLOSE_EVENT）
if sys.platform == "win32":
    from ctypes import wintypes
    _kernel32 = ctypes.windll.kernel32
    _handler_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

    @_handler_type
    def _console_handler(dwCtrlType):
        if dwCtrlType == 2:  # CTRL_CLOSE_EVENT — 用户点击 X 关闭窗口
            _kill_child()
        return False  # 交给默认处理程序继续执行

    _kernel32.SetConsoleCtrlHandler(_console_handler, 1)

atexit.register(_kill_child)


def console_input(prompt):
    """绕过 stdin（可能被 NUL 重定向），直接从控制台读取一行输入"""
    print(prompt, end='', flush=True)
    chars = []
    while True:
        ch = msvcrt.getwch()
        if ch == '\r':
            print()
            return ''.join(chars)
        if ch == '\b' and chars:
            chars.pop()
            print('\b \b', end='', flush=True)
        elif ch == '\x03':
            raise KeyboardInterrupt
        elif ch not in ('\x00', '\xe0', '\b'):
            chars.append(ch)
            print(ch, end='', flush=True)


def press_any_key(msg="按任意键退出……"):
    print(msg, end='', flush=True)
    msvcrt.getch()
    print()

def welcome():                
    print()
    print("                                      o")                                                                           
    print("    ■     ■■■■■■■■■■■■■■■■■■■■■■■■■■■ |")                                       
    print("  ■ ■ ■   ■   ■■■             ■■■   ■ |")                                       
    print("    ■     ■      ■■■■     ■■■■      ■■■")                                       
    print("          ■          ■■■■■          ■ ■")                                       
    print("          ■   ■■■■■         ■■■■■   ■ ■")                                       
    print("          ■   ■■■■■         ■■■■■   ■■■")                                       
    print("          ■-----o      W            ■")                                       
    print("          ■■■■■■■■■■■■■■■■■■■■■■■■■■■")                                       
    print()    
    print("              欢迎使用小信使 =w=")
    print("              WeeMessenger v1.0.2")
    print()
    print("  ==============================================")
    print("    启动准备")
    print("  ==============================================")
    print()
    print("    首次使用小信使前，请您手动完成以下准备操作")
    print()
    print("    1. 打开并进入微信客户端")
    print("    2. 使用快捷键 Ctrl+F 搜索并进入需要回复")
    print("       消息的群聊")
    print("    3. 重复第 2 步 2-3 次，确保目标群聊出现")
    print("       在搜索结果首位")
    print()
    print("    >  以上操作可确保自动搜索功能不再受到微信")
    print("       “搜索网络结果”的影响，仅需执行一次，永")
    print("       久生效~")
    print()
    print("    4. 打开根目录的 config.yaml ，编辑配置后")
    print("       保存并重启程序")
    print()
    print("  ==============================================")
    print()


def menu():
    print()
    print("  ==============================================")
    print("    启动菜单")
    print("  ==============================================")
    print()
    print("    [1] 标准模式 - 接收 WebSocket 消息并自动")
    print("                   发送至对应聊天")
    print("    [2] 调试模式 - 控制台输入消息后自动发送至")
    print("                   「文件传输助手」")
    print()
    print("  ==============================================")
    print()


def ensure_venv():
    if not os.path.exists(VENV_PYTHON):
        logger.info("[WeeMessenger - 提示] 正在创建虚拟环境……")
        result = subprocess.run([sys.executable, "-m", "venv", "venv"], cwd=BASE_DIR)
        if result.returncode != 0:
            logger.error("[WeeMessenger - 错误] 创建虚拟环境失败，请检查 Python 是否已安装且在系统路径中")
            press_any_key()
            sys.exit(1)
        logger.info("[WeeMessenger - 提示] 虚拟环境创建成功！")


def install_deps():
    logger.info("[WeeMessenger - 提示] 正在检查依赖……")
    result = subprocess.run(
        [VENV_PYTHON, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
        cwd=BASE_DIR,
    )
    if result.returncode != 0:
        logger.error("[WeeMessenger - 错误] 依赖安装失败……")
        press_any_key()
        sys.exit(1)


def main():
    global _child_proc

    # 启动前清理上一次残留的 main.py 进程
    _cleanup_stale_instance()

    welcome()

    args = list(sys.argv[1:])

    if not args:
        menu()
        choice = console_input("请输入 1 或 2 选择模式: ").strip()
        if choice == "1":
            print()
            logger.info("[WeeMessenger - 提示] 您选择了标准模式~")
            print()
        elif choice == "2":
            print()
            logger.info("[WeeMessenger - 提示] 您选择了调试模式~")
            print()
            args = ["--debug"]
        else:
            logger.warning("[WeeMessenger - 警告] 无效选择，请输入 1 或 2 哦！")
            press_any_key()
            sys.exit(1)

    ensure_venv()
    install_deps()

    logger.info("[WeeMessenger - 提示] 正在启动小信使……")

    try:
        with open("CONIN$", "r") as conin:
            _child_proc = subprocess.Popen(
                [VENV_PYTHON, "main.py"] + args,
                cwd=BASE_DIR,
                stdin=conin,
            )
            _save_child_pid(_child_proc.pid)
            _child_proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        _kill_child()
        _remove_pid_file()


if __name__ == "__main__":
    main()
