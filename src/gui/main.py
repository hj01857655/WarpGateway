"""GUI 主入口"""
import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .window import MainWindow


def setup_logging():
    """设置日志"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'warp_gateway_gui.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def main():
    """主函数"""
    setup_logging()
    
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
