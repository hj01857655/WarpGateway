"""Warp 应用管理工具"""
import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 平台相关依赖（仅在 Windows 使用）
if sys.platform == 'win32':
    try:
        import winreg  # type: ignore
    except Exception:  # pragma: no cover
        winreg = None  # type: ignore

# 可选的自定义路径（由 GUI 设置）
_CUSTOM_WARP_PATH: Optional[Path] = None


def set_custom_warp_path(path: str | Path) -> None:
    """设置自定义 Warp 可执行文件路径"""
    global _CUSTOM_WARP_PATH
    p = Path(path)
    _CUSTOM_WARP_PATH = p if p.exists() else None


def _query_registry_for_warp() -> Optional[Path]:
    """在注册表中查找 Warp 可执行路径（Windows）"""
    if sys.platform != 'win32' or winreg is None:  # type: ignore
        return None

    # 1) App Paths: HKLM/HKCU ...\App Paths\warp.exe
    app_paths = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\warp.exe"
    for root_name, root in [("HKCU", winreg.HKEY_CURRENT_USER), ("HKLM", winreg.HKEY_LOCAL_MACHINE)]:  # type: ignore
        for flag in (0, getattr(winreg, 'KEY_WOW64_64KEY', 0), getattr(winreg, 'KEY_WOW64_32KEY', 0)):
            try:
                key = winreg.OpenKey(root, app_paths, 0, winreg.KEY_READ | flag)  # type: ignore
                try:
                    # 默认值通常是完整路径
                    val, _ = winreg.QueryValueEx(key, None)  # type: ignore
                    p = Path(val.strip('"'))
                    if p.exists():
                        logger.info(f"✅ 从注册表找到 Warp: {root_name}\\{app_paths}")
                        return p
                    # 或者组合 Path + warp.exe
                    path_val, _ = winreg.QueryValueEx(key, 'Path')  # type: ignore
                    p = Path(path_val) / 'warp.exe'
                    if p.exists():
                        return p
                finally:
                    winreg.CloseKey(key)  # type: ignore
            except OSError:
                pass

    # 2) Uninstall keys: 查找包含 "Warp" 的 DisplayName
    uninstall_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    for root_name2, root in [("HKCU", winreg.HKEY_CURRENT_USER), ("HKLM", winreg.HKEY_LOCAL_MACHINE)]:  # type: ignore
        for sub in uninstall_paths:
            for flag in (0, getattr(winreg, 'KEY_WOW64_64KEY', 0), getattr(winreg, 'KEY_WOW64_32KEY', 0)):
                try:
                    base = winreg.OpenKey(root, sub, 0, winreg.KEY_READ | flag)  # type: ignore
                except OSError:
                    continue
                try:
                    i = 0
                    while True:
                        try:
                            name = winreg.EnumKey(base, i)  # type: ignore
                            i += 1
                        except OSError:
                            break
                        try:
                            key = winreg.OpenKey(base, name, 0, winreg.KEY_READ | flag)  # type: ignore
                        except OSError:
                            continue
                        try:
                            try:
                                display, _ = winreg.QueryValueEx(key, 'DisplayName')  # type: ignore
                            except OSError:
                                display = ''
                            if display and 'warp' in str(display).lower():
                                # 尝试 InstallLocation
                                try:
                                    loc, _ = winreg.QueryValueEx(key, 'InstallLocation')  # type: ignore
                                    p = Path(loc) / 'warp.exe'
                                    if p.exists():
                                        logger.info(f"✅ 从 Uninstall 注册表找到 Warp (InstallLocation): {root_name2}\\{sub}\\{name}")
                                        return p
                                except OSError:
                                    pass
                                # 尝试 DisplayIcon
                                try:
                                    icon, _ = winreg.QueryValueEx(key, 'DisplayIcon')  # type: ignore
                                    # 形如: "C:\\...\\warp.exe",0 或 C:\\...\\warp.exe
                                    icon_path = str(icon).split(',')[0].strip().strip('"')
                                    p = Path(icon_path)
                                    if p.exists():
                                        logger.info(f"✅ 从 Uninstall 注册表找到 Warp (DisplayIcon): {root_name2}\\{sub}\\{name}")
                                        return p
                                except OSError:
                                    pass
                        finally:
                            winreg.CloseKey(key)  # type: ignore
                finally:
                    winreg.CloseKey(base)  # type: ignore

    return None


def get_warp_path() -> Path:
    """获取 Warp 可执行文件路径（优先使用 自定义 > 环境变量 > 注册表 > 默认路径）"""
    # 1) 自定义路径
    if _CUSTOM_WARP_PATH and _CUSTOM_WARP_PATH.exists():
        return _CUSTOM_WARP_PATH
    
    # 2) 环境变量
    env_path = os.environ.get('WARP_PATH')
    if env_path and Path(env_path).exists():
        return Path(env_path)

    # 3) 注册表 (Windows)
    reg_path = _query_registry_for_warp()
    if reg_path and reg_path.exists():
        return reg_path
    
    # 4) 默认路径
    if sys.platform == 'win32':
        # Windows 默认路径
        warp_path = Path.home() / 'AppData' / 'Local' / 'Programs' / 'Warp' / 'warp.exe'
    elif sys.platform == 'darwin':
        # macOS 默认路径
        warp_path = Path('/Applications/Warp.app/Contents/MacOS/Warp')
    else:
        # Linux 默认路径
        warp_path = Path.home() / '.local' / 'share' / 'warp-terminal' / 'warp'
    
    return warp_path


def is_warp_installed():
    """检查 Warp 是否已安装"""
    warp_path = get_warp_path()
    return warp_path.exists()


def get_warp_version() -> Optional[str]:
    """从注册表获取 Warp 版本号"""
    if sys.platform != 'win32' or winreg is None:  # type: ignore
        return None
    
    # 尝试 HKCU 和 HKLM
    uninstall_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):  # type: ignore
        for sub in uninstall_paths:
            for flag in (0, getattr(winreg, 'KEY_WOW64_64KEY', 0)):
                try:
                    base = winreg.OpenKey(root, sub, 0, winreg.KEY_READ | flag)  # type: ignore
                except OSError:
                    continue
                try:
                    i = 0
                    while True:
                        try:
                            name = winreg.EnumKey(base, i)  # type: ignore
                            i += 1
                        except OSError:
                            break
                        try:
                            key = winreg.OpenKey(base, name, 0, winreg.KEY_READ | flag)  # type: ignore
                        except OSError:
                            continue
                        try:
                            try:
                                display, _ = winreg.QueryValueEx(key, 'DisplayName')  # type: ignore
                            except OSError:
                                display = ''
                            if display and 'warp' in str(display).lower():
                                try:
                                    version, _ = winreg.QueryValueEx(key, 'DisplayVersion')  # type: ignore
                                    return str(version)
                                except OSError:
                                    pass
                        finally:
                            winreg.CloseKey(key)  # type: ignore
                finally:
                    winreg.CloseKey(base)  # type: ignore
    
    return None


def launch_warp():
    """启动 Warp 应用"""
    warp_path = get_warp_path()
    
    if not warp_path.exists():
        logger.error(f"❌ Warp 未安装，路径不存在: {warp_path}")
        return False
    
    try:
        if sys.platform == 'win32':
            subprocess.Popen([str(warp_path)], shell=False)
        else:
            subprocess.Popen([str(warp_path)])
        
        logger.info(f"✅ Warp 已启动: {warp_path}")
        return True
    except Exception as e:
        logger.error(f"❌ 启动 Warp 失败: {e}")
        return False


def kill_warp():
    """关闭 Warp 进程"""
    try:
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/F', '/IM', 'warp.exe'], 
                          capture_output=True, check=False)
        elif sys.platform == 'darwin':
            subprocess.run(['killall', 'Warp'], 
                          capture_output=True, check=False)
        else:
            subprocess.run(['pkill', '-f', 'warp'], 
                          capture_output=True, check=False)
        
        logger.info("✅ Warp 进程已终止")
        return True
    except Exception as e:
        logger.error(f"❌ 终止 Warp 失败: {e}")
        return False


def is_warp_running():
    """检查 Warp 是否正在运行"""
    try:
        if sys.platform == 'win32':
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq warp.exe'],
                capture_output=True,
                text=True
            )
            return 'warp.exe' in result.stdout
        elif sys.platform == 'darwin':
            result = subprocess.run(
                ['pgrep', '-x', 'Warp'],
                capture_output=True
            )
            return result.returncode == 0
        else:
            result = subprocess.run(
                ['pgrep', '-f', 'warp'],
                capture_output=True
            )
            return result.returncode == 0
    except Exception as e:
        logger.error(f"检查 Warp 运行状态失败: {e}")
        return False


def restart_warp():
    """重启 Warp 应用"""
    logger.info("🔄 正在重启 Warp...")
    kill_warp()
    import time
    time.sleep(1)  # 等待进程完全关闭
    return launch_warp()


def main():
    """命令行入口"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'launch':
            launch_warp()
        elif cmd == 'kill':
            kill_warp()
        elif cmd == 'restart':
            restart_warp()
        elif cmd == 'status':
            if is_warp_installed():
                print(f"✅ Warp 已安装: {get_warp_path()}")
                if is_warp_running():
                    print("✅ Warp 正在运行")
                else:
                    print("⭕ Warp 未运行")
            else:
                print(f"❌ Warp 未安装")
    else:
        print("用法:")
        print("  python -m src.utils.warp_manager launch   # 启动 Warp")
        print("  python -m src.utils.warp_manager kill     # 关闭 Warp")
        print("  python -m src.utils.warp_manager restart  # 重启 Warp")
        print("  python -m src.utils.warp_manager status   # 检查状态")


if __name__ == '__main__':
    main()
