"""桌面窗口应用"""
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from threading import Thread

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QTextEdit, QFileDialog, QMenu, QLineEdit
)
from PySide6.QtCore import QTimer, Signal, QObject
from PySide6.QtGui import QFont, QCursor

from ..core.config import Config
from ..utils.cert_manager import check_cert_installed, install_cert
from ..utils.warp_manager import (
    launch_warp, restart_warp, get_warp_path, set_custom_warp_path, get_warp_version
)


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


class WindowSignals(QObject):
    """信号类"""
    status_changed = Signal(str)
    log_message = Signal(str)


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        self.config = Config()
        self.proxy_thread = None
        self.signals = WindowSignals()
        
        self.setWindowTitle('WarpGateway')
        self.setMinimumSize(600, 400)
        
        # 创建界面
        self._create_ui()
        
        # 定时更新状态
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_status)
        self.timer.start(2000)
        
        # 检查证书
        QTimer.singleShot(1000, self._check_cert)
    
    def _create_ui(self):
        """创建界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 标题
        title = QLabel('WarpGateway 代理网关')
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 状态显示
        self.status_label = QLabel('状态: 已停止')
        status_font = QFont()
        status_font.setPointSize(12)
        self.status_label.setFont(status_font)
        layout.addWidget(self.status_label)
        
        # 地址显示
        self.address_label = QLabel(f'监听地址: {self.config.proxy.host}:{self.config.proxy.port}')
        layout.addWidget(self.address_label)
        
        # Warp 路径选择器
        warp_path_layout = QHBoxLayout()
        warp_path_label = QLabel('Warp 路径:')
        warp_path_layout.addWidget(warp_path_label)
        
        self.warp_path_edit = QLineEdit()
        self.warp_path_edit.setReadOnly(True)
        default_warp = get_warp_path()
        self.warp_path_edit.setText(str(default_warp))
        warp_path_layout.addWidget(self.warp_path_edit, 1)
        
        warp_browse_btn = QPushButton('选择...')
        warp_browse_btn.clicked.connect(self._browse_warp_path)
        warp_path_layout.addWidget(warp_browse_btn)
        
        layout.addLayout(warp_path_layout)
        
        # Warp 版本显示
        warp_version = get_warp_version()
        version_text = f'Warp 版本: {warp_version}' if warp_version else 'Warp 版本: 未检测到'
        self.warp_version_label = QLabel(version_text)
        layout.addWidget(self.warp_version_label)
        
        # 按钮
        main_layout = QHBoxLayout()
        
        self.main_button = QPushButton('一键启动')
        self.main_button.setMinimumHeight(50)
        self.main_button.clicked.connect(self._toggle_main)
        main_layout.addWidget(self.main_button)
        
        layout.addLayout(main_layout)
        
        # 状态追踪
        self.is_running = False
        
        # 辅助按钮（动态切换）
        tools_layout = QHBoxLayout()
        
        self.config_button = QPushButton('备份配置')
        self.config_button.setMinimumHeight(35)
        self.config_button.clicked.connect(self._toggle_config)
        tools_layout.addWidget(self.config_button)
        
        layout.addLayout(tools_layout)
        
        # 配置状态追踪
        self.config_is_backup = True  # True=显示备份, False=显示恢复
        
        # 日志显示
        log_label = QLabel('日志:')
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # 连接信号
        self.signals.log_message.connect(self._append_log)
    
    def _toggle_main(self):
        """主按钮切换（启动/停止）"""
        if self.is_running:
            self._stop_all()
        else:
            self._start_all()
    
    def _start_all(self):
        """一键启动（带进度显示）"""
        self._log('========== 开始一键启动 ==========')
        
        # 1. 检查证书
        self.main_button.setText('检查证书...')
        self.main_button.setEnabled(False)
        QApplication.processEvents()
        
        self._log('1. 检查证书...')
        if not check_cert_installed():
            self._log('   证书未安装，正在安装...')
            if not install_cert():
                self._log('❌ 证书安装失败，无法继续')
                self.main_button.setText('一键启动')
                self.main_button.setEnabled(True)
                return
            self._log('   ✅ 证书安装成功')
        else:
            self._log('   ✅ 证书已安装')
        
        # 2. 启动代理
        self.main_button.setText('启动代理服务...')
        QApplication.processEvents()
        
        self._log('2. 启动代理服务...')
        if not self._start_proxy():
            self._log('❌ 代理启动失败，无法继续')
            self.main_button.setText('一键启动')
            self.main_button.setEnabled(True)
            return
        self._log('   ✅ 代理已启动')
        
        # 3. 启动 Warp
        self.main_button.setText('启动 Warp...')
        QApplication.processEvents()
        
        self._log('3. 启动 Warp...')
        if launch_warp():
            self._log('   ✅ Warp 已启动')
        else:
            self._log('   ⚠️ Warp 启动失败（可能已在运行）')
        
        self._log('========== 启动完成 ==========')
        self._log('现在可以在 Warp 中使用代理了')
        
        # 更新状态
        self.is_running = True
        self.main_button.setText('停止服务')
        self.main_button.setEnabled(True)
    
    def _stop_all(self):
        """停止所有服务"""
        self._log('========== 停止服务 ==========')
        
        self.main_button.setText('停止中...')
        self.main_button.setEnabled(False)
        QApplication.processEvents()
        
        # 停止代理
        self._stop_proxy()
        
        self._log('========== 已停止 ==========')
        
        # 更新状态
        self.is_running = False
        self.main_button.setText('一键启动')
        self.main_button.setEnabled(True)
    
    def _start_proxy(self):
        """启动代理"""
        if self.proxy_thread and self.proxy_thread.running:
            self._log('   代理已在运行中')
            return True
        
        self.proxy_thread = ProxyThread(self.config)
        self.proxy_thread.start()
        return True
    
    def _stop_proxy(self):
        """停止代理"""
        if not self.proxy_thread or not self.proxy_thread.running:
            self._log('   代理未运行')
            return
        
        self.proxy_thread.stop()
        self.proxy_thread = None
        self._log('   ✅ 代理已停止')
    
    def _update_status(self):
        """更新状态"""
        if self.proxy_thread and self.proxy_thread.running:
            self.status_label.setText('状态: 运行中 ✅')
        else:
            self.status_label.setText('状态: 已停止 ⭕')
    
    def _check_cert(self):
        """检查证书"""
        try:
            if not check_cert_installed():
                self._log('⚠️ 证书未安装，请点击【安装证书】按钮')
            else:
                self._log('✅ 证书已安装')
        except Exception as e:
            self._log(f'证书检查错误: {e}')
    
    def _browse_warp_path(self):
        """选择 Warp 可执行文件路径"""
        start_dir = str(get_warp_path().parent)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '选择 Warp 可执行文件',
            start_dir,
            '可执行文件 (*.exe *);;所有文件 (*)'
        )
        if not file_path:
            return
        p = Path(file_path)
        if not p.exists():
            self._log(f'❌ 无效路径: {file_path}')
            return
        set_custom_warp_path(p)
        self.warp_path_edit.setText(str(p))
        self._log(f'✅ 已设置 Warp 路径: {p}')
    
    def _install_cert(self):
        """安装证书"""
        self._log('正在安装证书...')
        try:
            if install_cert():
                self._log('✅ 证书安装成功')
            else:
                self._log('❌ 证书安装失败，请检查日志')
        except Exception as e:
            self._log(f'❌ 证书安装错误: {e}')
    
    
    def _restart_warp(self):
        """重启 Warp"""
        self._log('🔄 正在重启 Warp...')
        try:
            if restart_warp():
                self._log('✅ Warp 已重启')
            else:
                self._log('❌ 重启 Warp 失败')
        except Exception as e:
            self._log(f'❌ 错误: {e}')
    
    def _toggle_config(self):
        """配置按钮切换（备份/恢复）"""
        if self.config_is_backup:
            self._backup_config()
        else:
            self._restore_config()
    
    def _backup_config(self):
        """备份配置到 backups/ 目录"""
        try:
            backups_dir = Path('backups')
            backups_dir.mkdir(exist_ok=True)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            src = Path('config.yaml')
            if not src.exists():
                self._log('❌ 未找到 config.yaml，无法备份')
                return
            dst = backups_dir / f'config_{ts}.yaml'
            shutil.copy2(src, dst)
            
            # 可选：备份 mcp 目录
            mcp_dir = Path('mcp')
            if mcp_dir.exists() and mcp_dir.is_dir():
                dst_mcp = backups_dir / f'mcp_{ts}'
                shutil.copytree(mcp_dir, dst_mcp)
                self._log(f'✅ 已备份 MCP 配置到 {dst_mcp}')
            
            self._log(f'✅ 已备份配置到 {dst}')
            # 切换按钮状态
            self.config_is_backup = False
            self.config_button.setText('恢复配置')
        except Exception as e:
            self._log(f'❌ 备份失败: {e}')
    
    def _restore_config(self):
        """从备份恢复配置"""
        try:
            backups_dir = str((Path.cwd() / 'backups'))
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                '选择备份文件',
                backups_dir,
                'YAML Files (*.yaml *.yml)'
            )
            if not file_path:
                return
            shutil.copy2(file_path, 'config.yaml')
            self.config = Config()  # 重新加载配置
            self.address_label.setText(f'监听地址: {self.config.proxy.host}:{self.config.proxy.port}')
            self._log(f'✅ 已从备份恢复: {file_path}')
            # 切换按钮状态
            self.config_is_backup = True
            self.config_button.setText('备份配置')
        except Exception as e:
            self._log(f'❌ 恢复失败: {e}')
    
    
        """添加日志"""
        self.signals.log_message.emit(message)
    
    def _append_log(self, message: str):
        """追加日志到文本框"""
        self.log_text.append(message)
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.proxy_thread and self.proxy_thread.running:
            self.proxy_thread.stop()
        self.timer.stop()
        event.accept()
