"""日志记录处理器"""

import json
import logging
from datetime import datetime
from pathlib import Path
from mitmproxy import http
from typing import Optional
from ..core.interceptor import BaseInterceptor

logger = logging.getLogger(__name__)


class LoggerHandler(BaseInterceptor):
    """日志记录处理器"""

    def __init__(self, log_dir: str = "logs"):
        super().__init__("LoggerHandler")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 创建请求日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"requests_{timestamp}.jsonl"
        
        logger.info(f"📁 Request log file: {self.log_file}")

    def request(self, flow: http.HTTPFlow) -> Optional[http.HTTPFlow]:
        """记录请求"""
        try:
            request_data = {
                "timestamp": datetime.now().isoformat(),
                "type": "request",
                "method": flow.request.method,
                "url": flow.request.pretty_url,
                "headers": dict(flow.request.headers),
                "content_length": len(flow.request.content) if flow.request.content else 0,
            }
            
            self._write_log(request_data)
        except Exception as e:
            logger.error(f"❌ Failed to log request: {e}")
        
        return None

    def response(self, flow: http.HTTPFlow) -> Optional[http.HTTPFlow]:
        """记录响应"""
        if not flow.response:
            return None
            
        try:
            response_data = {
                "timestamp": datetime.now().isoformat(),
                "type": "response",
                "method": flow.request.method,
                "url": flow.request.pretty_url,
                "status_code": flow.response.status_code,
                "headers": dict(flow.response.headers),
                "content_length": len(flow.response.content) if flow.response.content else 0,
            }
            
            self._write_log(response_data)
        except Exception as e:
            logger.error(f"❌ Failed to log response: {e}")
        
        return None

    def _write_log(self, data: dict):
        """写入日志文件"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
