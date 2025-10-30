"""代理服务器启动模块"""

import sys
import logging
import argparse
import signal
from pathlib import Path
from mitmproxy.tools.main import mitmdump
from .config import Config
from .interceptor import InterceptorChain
from ..handlers import WarpHandler, LoggerHandler, StatsHandler, AIMonitorHandler


def setup_logging(config: Config):
    """设置日志"""
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    # 创建日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 根日志配置
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 控制台输出
    if config.log_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 文件输出
    if config.log_file:
        file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


class ProxyServer:
    """代理服务器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.chain = InterceptorChain()
        self.stats_handler = None
        
    def setup_handlers(self):
        """设置处理器"""
        # 添加 Warp 处理器
        warp_handler = WarpHandler(self.config)
        self.chain.add(warp_handler)
        
        # 添加 AI 状态监控处理器
        ai_monitor = AIMonitorHandler()
        self.chain.add(ai_monitor)
        
        # 添加日志处理器
        logger_handler = LoggerHandler("logs")
        self.chain.add(logger_handler)
        
        # 添加统计处理器
        self.stats_handler = StatsHandler()
        self.chain.add(self.stats_handler)
        
    def request(self, flow):
        """处理请求"""
        self.chain.request(flow)
        
    def response(self, flow):
        """处理响应"""
        self.chain.response(flow)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="WarpGateway - Warp.dev Proxy Gateway")
    parser.add_argument(
        "--config",
        "-c",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)"
    )
    parser.add_argument(
        "--host",
        help="代理监听地址 (覆盖配置文件)"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="代理监听端口 (覆盖配置文件)"
    )
    parser.add_argument(
        "--no-stats",
        action="store_true",
        help="禁用统计功能"
    )
    
    args = parser.parse_args()

    # 加载配置
    config = Config(args.config)
    
    # 设置日志
    setup_logging(config)
    logger = logging.getLogger(__name__)

    # 命令行参数覆盖配置
    host = args.host or config.proxy_host
    port = args.port or config.proxy_port

    logger.info("=" * 60)
    logger.info("🚀 WarpGateway Starting...")
    logger.info(f"📍 Proxy Address: {host}:{port}")
    logger.info(f"📋 Config File: {Path(args.config).absolute()}")
    logger.info(f"🚫 Block Rules: {len(config.block_rules)} patterns")
    logger.info(f"✅ Allow Rules: {len(config.allow_rules)} patterns")
    logger.info(f"📝 Log Only Rules: {len(config.log_only_rules)} patterns")
    logger.info("=" * 60)

    # 创建代理服务器
    proxy = ProxyServer(config)
    proxy.setup_handlers()
    
    # 设置信号处理
    def signal_handler(sig, frame):
        if proxy.stats_handler and not args.no_stats:
            proxy.stats_handler.print_stats()
        logger.info("\n👋 WarpGateway Stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)

    # 启动 mitmproxy
    try:
        mitmdump_args = [
            "--listen-host", host,
            "--listen-port", str(port),
            "--set", "confdir=~/.mitmproxy",
        ]
        
        if config.ssl_insecure:
            mitmdump_args.append("--ssl-insecure")

        sys.argv = ["mitmdump"] + mitmdump_args
        
        # 启动
        mitmdump([proxy])
        
    except KeyboardInterrupt:
        if proxy.stats_handler and not args.no_stats:
            proxy.stats_handler.print_stats()
        logger.info("\n👋 WarpGateway Stopped")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
