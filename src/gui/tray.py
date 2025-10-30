"""系统托盘应用"""
import sys
import subprocess
import webbrowser
from pathlib import Path
from threading import Thread

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QTimer, Signal, QObject

from ..core.config import Config
from ..handlers.stats import StatsManager


class ProxyThread(Thread):
    """代理服务器后台线程"""
    
    def __init__(self, config: Config):
        super().__init__(daemon=True)
        self.config = config
        self.process = None
        self.running = False
    
    def run(self):
        """运行 mitmproxy"""
        self.running = True
        cmd = [
            'mitmdump',
            '-s', str(Path(__file__).parent.parent / 'core' / 'interceptor.py'),
            '--listen-host', self.config.proxy.host,
            '--listen-port', str(self.config.proxy.port),
            '--set', f'confdir={self.config.proxy.cert_dir}',
        ]
        
        if self.config.proxy.upstream:
            cmd.extend(['--mode', f'upstream:{self.config.proxy.upstream}'])
        
        self.process = subprocess.Popen(cmd)
        self.process.wait()
        self.running = False
    
    def stop(self):
        """停止代理"""
        self.running = False
        if self.process:
            self.process.terminate()
            self.process.wait()


class TraySignals(QObject):
    """信号类"""
    status_changed = Signal(str)


class TrayApp(QSystemTrayIcon):
    """系统托盘应用"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 加载配置
        self.config = Config()
        self.stats = StatsManager()
        self.proxy_thread = None
        self.signals = TraySignals()
        
        # 设置托盘图标
        self.setIcon(self._create_icon())
        self.setToolTip('WarpGateway - 已停止')
        
        # 创建菜单
        self._create_menu()
        
        # 显示托盘图标
        self.show()
        
        # 定时更新状态
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_status)
        self.timer.start(2000)  # 每2秒更新
    
    def _create_icon(self):
        """创建托盘图标（使用内置图标）"""
        # 这里使用 Qt 内置图标，后续可以替换为自定义图标
        from PySide6.QtWidgets import QStyle
        app = QApplication.instance()
        return app.style().standardIcon(QStyle.SP_ComputerIcon)
    
    def _create_menu(self):
        """创建托盘菜单"""
        menu = QMenu()
        
        # 启动/停止代理
        self.toggle_action = QAction('启动代理', self)
        self.toggle_action.triggered.connect(self._toggle_proxy)
        menu.addAction(self.toggle_action)
        
        menu.addSeparator()
        
        # 查看状态
        status_action = QAction('查看状态', self)
        status_action.triggered.connect(self._show_status)
        menu.addAction(status_action)
        
        # 打开日志目录
        logs_action = QAction('打开日志目录', self)
        logs_action.triggered.connect(self._open_logs)
        menu.addAction(logs_action)
        
        # 打开配置文件
        config_action = QAction('打开配置文件', self)
        config_action.triggered.connect(self._open_config)
        menu.addAction(config_action)
        
        menu.addSeparator()
        
        # 重新加载配置
        reload_action = QAction('重新加载配置', self)
        reload_action.triggered.connect(self._reload_config)
        menu.addAction(reload_action)
        
        menu.addSeparator()
        
        # 退出
        quit_action = QAction('退出', self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)
        
        self.setContextMenu(menu)
    
    def _toggle_proxy(self):
        """切换代理状态"""
        if self.proxy_thread and self.proxy_thread.running:
            self._stop_proxy()
        else:
            self._start_proxy()
    
    def _start_proxy(self):
        """启动代理"""
        if self.proxy_thread and self.proxy_thread.running:
            self.showMessage('WarpGateway', '代理已在运行中', QSystemTrayIcon.Information)
            return
        
        self.proxy_thread = ProxyThread(self.config)
        self.proxy_thread.start()
        
        self.toggle_action.setText('停止代理')
        self.setToolTip(f'WarpGateway - 运行中 ({self.config.proxy.host}:{self.config.proxy.port})')
        self.showMessage('WarpGateway', f'代理已启动\n监听地址: {self.config.proxy.host}:{self.config.proxy.port}', 
                        QSystemTrayIcon.Information, 2000)
    
    def _stop_proxy(self):
        """停止代理"""
        if not self.proxy_thread or not self.proxy_thread.running:
            self.showMessage('WarpGateway', '代理未运行', QSystemTrayIcon.Information)
            return
        
        self.proxy_thread.stop()
        self.proxy_thread = None
        
        self.toggle_action.setText('启动代理')
        self.setToolTip('WarpGateway - 已停止')
        self.showMessage('WarpGateway', '代理已停止', QSystemTrayIcon.Information, 2000)
    
    def _show_status(self):
        """显示状态信息"""
        status = "代理运行中" if (self.proxy_thread and self.proxy_thread.running) else "代理已停止"
        
        stats = self.stats.get_stats()
        message = f"""状态: {status}
监听地址: {self.config.proxy.host}:{self.config.proxy.port}

统计信息:
总请求数: {stats.get('total_requests', 0)}
成功: {stats.get('success_count', 0)}
失败: {stats.get('error_count', 0)}
"""
        
        self.showMessage('WarpGateway 状态', message, QSystemTrayIcon.Information, 5000)
    
    def _open_logs(self):
        """打开日志目录"""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        if sys.platform == 'win32':
            subprocess.run(['explorer', str(log_dir.absolute())])
        elif sys.platform == 'darwin':
            subprocess.run(['open', str(log_dir.absolute())])
        else:
            subprocess.run(['xdg-open', str(log_dir.absolute())])
    
    def _open_config(self):
        """打开配置文件"""
        config_file = Path('config.yaml')
        
        if sys.platform == 'win32':
            subprocess.run(['notepad', str(config_file.absolute())])
        elif sys.platform == 'darwin':
            subprocess.run(['open', '-e', str(config_file.absolute())])
        else:
            subprocess.run(['xdg-open', str(config_file.absolute())])
    
    def _reload_config(self):
        """重新加载配置"""
        try:
            self.config = Config()
            self.showMessage('WarpGateway', '配置已重新加载', QSystemTrayIcon.Information, 2000)
        except Exception as e:
            self.showMessage('WarpGateway', f'配置加载失败: {str(e)}', QSystemTrayIcon.Critical, 3000)
    
    def _update_status(self):
        """更新状态"""
        if self.proxy_thread and self.proxy_thread.running:
            stats = self.stats.get_stats()
            tooltip = f"""WarpGateway - 运行中
地址: {self.config.proxy.host}:{self.config.proxy.port}
请求数: {stats.get('total_requests', 0)}"""
            self.setToolTip(tooltip)
    
    def _quit(self):
        """退出应用"""
        if self.proxy_thread and self.proxy_thread.running:
            self.proxy_thread.stop()
        
        self.timer.stop()
        QApplication.quit()
