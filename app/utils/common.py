import platform

from app.consts import consts


def get_os_type():
    system = platform.system().lower()

    if system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    elif system == "darwin":  # macOS的系统标识是'darwin'
        return consts.SYS_TYPE_MAC_OS
    else:
        return "unknown"


def is_mac_os():
    return get_os_type() == consts.SYS_TYPE_MAC_OS
