"""配置管理模块"""

import yaml
from pathlib import Path
from typing import Dict, List, Any


class Config:
    """配置管理类"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            return self._default_config()

        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "proxy": {"host": "0.0.0.0", "port": 8080, "ssl_insecure": False},
            "rules": {"block": [], "allow": [], "log_only": []},
            "logging": {"level": "INFO", "file": "warp_gateway.log", "console": True},
        }

    @property
    def proxy_host(self) -> str:
        return self.config.get("proxy", {}).get("host", "0.0.0.0")

    @property
    def proxy_port(self) -> int:
        return self.config.get("proxy", {}).get("port", 8080)

    @property
    def ssl_insecure(self) -> bool:
        return self.config.get("proxy", {}).get("ssl_insecure", False)

    @property
    def block_rules(self) -> List[str]:
        return self.config.get("rules", {}).get("block", [])

    @property
    def allow_rules(self) -> List[str]:
        return self.config.get("rules", {}).get("allow", [])

    @property
    def log_only_rules(self) -> List[str]:
        return self.config.get("rules", {}).get("log_only", [])

    @property
    def log_level(self) -> str:
        return self.config.get("logging", {}).get("level", "INFO")

    @property
    def log_file(self) -> str:
        return self.config.get("logging", {}).get("file", "warp_gateway.log")

    @property
    def log_console(self) -> bool:
        return self.config.get("logging", {}).get("console", True)

    @property
    def streaming_paths(self) -> List[str]:
        return self.config.get("streaming", {}).get("paths", [])
    
    @property
    def upstream(self) -> str:
        """默认上游代理"""
        return self.config.get("proxy", {}).get("upstream", "")
    
    @property
    def upstream_routes(self) -> List[Dict[str, str]]:
        """条件上游代理路由"""
        return self.config.get("proxy", {}).get("upstream_routes", [])
    
    def get_upstream_for_url(self, url: str) -> str:
        """根据 URL 获取对应的上游代理"""
        # 先检查条件路由
        for route in self.upstream_routes:
            pattern = route.get("pattern", "")
            if pattern and pattern in url:
                return route.get("upstream", "")
        # 返回默认上游代理
        return self.upstream
