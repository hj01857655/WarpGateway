"""mitmproxy 证书自动安装工具"""
import os
import sys
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_cert_path():
    """获取 mitmproxy 证书路径"""
    if sys.platform == 'win32':
        cert_dir = Path.home() / '.mitmproxy'
        cert_file = cert_dir / 'mitmproxy-ca-cert.cer'
    else:
        cert_dir = Path.home() / '.mitmproxy'
        cert_file = cert_dir / 'mitmproxy-ca-cert.pem'
    
    return cert_file


def install_cert_windows(cert_file):
    """Windows 系统安装证书"""
    try:
        # 使用 certutil 安装证书到受信任的根证书颁发机构
        cmd = [
            'certutil',
            '-addstore',
            'Root',
            str(cert_file)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            logger.info("✅ 证书安装成功")
            return True
        else:
            logger.error(f"❌ 证书安装失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 证书安装异常: {e}")
        return False


def install_cert_macos(cert_file):
    """macOS 系统安装证书"""
    try:
        cmd = [
            'sudo',
            'security',
            'add-trusted-cert',
            '-d',
            '-r', 'trustRoot',
            '-k', '/Library/Keychains/System.keychain',
            str(cert_file)
        ]
        
        result = subprocess.run(cmd, check=False)
        
        if result.returncode == 0:
            logger.info("✅ 证书安装成功")
            return True
        else:
            logger.error("❌ 证书安装失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 证书安装异常: {e}")
        return False


def install_cert_linux(cert_file):
    """Linux 系统安装证书"""
    try:
        # 不同发行版路径可能不同
        cert_dirs = [
            Path('/usr/local/share/ca-certificates'),
            Path('/etc/pki/ca-trust/source/anchors'),
        ]
        
        for cert_dir in cert_dirs:
            if cert_dir.exists():
                target = cert_dir / 'mitmproxy-ca-cert.crt'
                
                # 复制证书
                subprocess.run(['sudo', 'cp', str(cert_file), str(target)], check=True)
                
                # 更新证书
                if cert_dir == cert_dirs[0]:
                    subprocess.run(['sudo', 'update-ca-certificates'], check=True)
                else:
                    subprocess.run(['sudo', 'update-ca-trust'], check=True)
                
                logger.info("✅ 证书安装成功")
                return True
        
        logger.error("❌ 未找到证书目录")
        return False
        
    except Exception as e:
        logger.error(f"❌ 证书安装异常: {e}")
        return False


def check_cert_installed():
    """检查证书是否已安装"""
    cert_file = get_cert_path()
    
    if not cert_file.exists():
        return False
    
    if sys.platform == 'win32':
        try:
            # Windows: 检查证书是否在受信任的根证书颁发机构中
            result = subprocess.run(
                ['certutil', '-verifystore', 'Root', 'mitmproxy'],
                capture_output=True,
                text=True,
                timeout=5  # 加入超时限制
            )
            return 'mitmproxy' in result.stdout
        except subprocess.TimeoutExpired:
            logger.warning("证书检查超时")
            return False
        except Exception as e:
            logger.error(f"证书检查失败: {e}")
            return False
    
    return False


def generate_cert():
    """生成 mitmproxy 证书"""
    logger.info("🔧 正在生成 mitmproxy 证书...")
    
    try:
        # 运行 mitmdump 生成证书
        result = subprocess.run(
            ['mitmdump', '--version'],
            capture_output=True,
            timeout=10
        )
        
        cert_file = get_cert_path()
        if cert_file.exists():
            logger.info(f"✅ 证书已生成: {cert_file}")
            return True
        else:
            logger.error("❌ 证书生成失败")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ 证书生成超时")
        return False
    except Exception as e:
        logger.error(f"❌ 证书生成异常: {e}")
        return False


def install_cert():
    """安装证书主函数"""
    # 检查是否已安装
    if check_cert_installed():
        logger.info("✅ 证书已安装")
        return True
    
    # 检查证书是否存在
    cert_file = get_cert_path()
    if not cert_file.exists():
        logger.info("📋 证书不存在，正在生成...")
        if not generate_cert():
            return False
    
    logger.info(f"📋 证书路径: {cert_file}")
    logger.info("🔧 开始安装证书...")
    
    # 根据系统选择安装方式
    if sys.platform == 'win32':
        return install_cert_windows(cert_file)
    elif sys.platform == 'darwin':
        return install_cert_macos(cert_file)
    else:
        return install_cert_linux(cert_file)


def uninstall_cert_windows():
    """Windows 卸载证书"""
    try:
        cmd = [
            'certutil',
            '-delstore',
            'Root',
            'mitmproxy'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ 证书卸载成功")
            return True
        else:
            logger.error(f"❌ 证书卸载失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 证书卸载异常: {e}")
        return False


def main():
    """命令行入口"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    if len(sys.argv) > 1 and sys.argv[1] == 'uninstall':
        if sys.platform == 'win32':
            uninstall_cert_windows()
        else:
            logger.error("❌ 当前系统不支持自动卸载")
    else:
        if install_cert():
            print("\n✅ 证书安装完成！")
            print("现在可以启动 WarpGateway 了。")
        else:
            print("\n❌ 证书安装失败！")
            print("请手动安装证书：")
            print(f"证书路径: {get_cert_path()}")
            if sys.platform == 'win32':
                print("双击证书文件，选择'安装证书'，放入'受信任的根证书颁发机构'")


if __name__ == '__main__':
    main()
