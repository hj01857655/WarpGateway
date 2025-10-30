"""统计分析处理器"""

import logging
from collections import defaultdict
from datetime import datetime
from mitmproxy import http
from typing import Optional, Dict
from ..core.interceptor import BaseInterceptor

logger = logging.getLogger(__name__)


class StatsHandler(BaseInterceptor):
    """统计分析处理器"""

    def __init__(self):
        super().__init__("StatsHandler")
        self.stats = {
            "total_requests": 0,
            "total_responses": 0,
            "blocked_requests": 0,
            "methods": defaultdict(int),
            "status_codes": defaultdict(int),
            "hosts": defaultdict(int),
        }
        self.start_time = datetime.now()

    def request(self, flow: http.HTTPFlow) -> Optional[http.HTTPFlow]:
        """统计请求"""
        self.stats["total_requests"] += 1
        self.stats["methods"][flow.request.method] += 1
        self.stats["hosts"][flow.request.host] += 1
        
        # 检查是否被拦截
        if flow.response and flow.response.status_code == 403:
            self.stats["blocked_requests"] += 1
        
        return None

    def response(self, flow: http.HTTPFlow) -> Optional[http.HTTPFlow]:
        """统计响应"""
        if flow.response:
            self.stats["total_responses"] += 1
            self.stats["status_codes"][flow.response.status_code] += 1
        
        return None

    def get_stats(self) -> Dict:
        """获取统计信息"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        return {
            **self.stats,
            "uptime_seconds": uptime,
            "requests_per_second": self.stats["total_requests"] / uptime if uptime > 0 else 0,
        }

    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        logger.info("=" * 60)
        logger.info("📊 Statistics:")
        logger.info(f"  Total Requests: {stats['total_requests']}")
        logger.info(f"  Total Responses: {stats['total_responses']}")
        logger.info(f"  Blocked Requests: {stats['blocked_requests']}")
        logger.info(f"  Uptime: {stats['uptime_seconds']:.2f}s")
        logger.info(f"  Requests/sec: {stats['requests_per_second']:.2f}")
        logger.info(f"  Methods: {dict(stats['methods'])}")
        logger.info(f"  Status Codes: {dict(stats['status_codes'])}")
        logger.info(f"  Top Hosts: {dict(list(stats['hosts'].items())[:5])}")
        logger.info("=" * 60)

    def reset(self):
        """重置统计"""
        self.stats = {
            "total_requests": 0,
            "total_responses": 0,
            "blocked_requests": 0,
            "methods": defaultdict(int),
            "status_codes": defaultdict(int),
            "hosts": defaultdict(int),
        }
        self.start_time = datetime.now()
        logger.info("🔄 Statistics reset")
