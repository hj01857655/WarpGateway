"""拦截器基类"""

import logging
from abc import ABC, abstractmethod
from mitmproxy import http
from typing import Optional

logger = logging.getLogger(__name__)


class BaseInterceptor(ABC):
    """拦截器基类"""

    def __init__(self, name: str = "BaseInterceptor"):
        self.name = name
        self.enabled = True

    @abstractmethod
    def request(self, flow: http.HTTPFlow) -> Optional[http.HTTPFlow]:
        """
        处理请求
        
        返回:
            - None: 继续处理
            - flow: 修改后的 flow（会阻止后续处理器）
        """
        pass

    @abstractmethod
    def response(self, flow: http.HTTPFlow) -> Optional[http.HTTPFlow]:
        """
        处理响应
        
        返回:
            - None: 继续处理
            - flow: 修改后的 flow（会阻止后续处理器）
        """
        pass

    def enable(self):
        """启用拦截器"""
        self.enabled = True
        logger.info(f"✅ {self.name} enabled")

    def disable(self):
        """禁用拦截器"""
        self.enabled = False
        logger.info(f"❌ {self.name} disabled")


class InterceptorChain:
    """拦截器链"""

    def __init__(self):
        self.interceptors: list[BaseInterceptor] = []

    def add(self, interceptor: BaseInterceptor):
        """添加拦截器"""
        self.interceptors.append(interceptor)
        logger.info(f"🔗 Added interceptor: {interceptor.name}")

    def remove(self, interceptor: BaseInterceptor):
        """移除拦截器"""
        if interceptor in self.interceptors:
            self.interceptors.remove(interceptor)
            logger.info(f"🔓 Removed interceptor: {interceptor.name}")

    def request(self, flow: http.HTTPFlow) -> None:
        """处理请求"""
        for interceptor in self.interceptors:
            if not interceptor.enabled:
                continue

            result = interceptor.request(flow)
            if result:  # 如果返回了修改后的 flow，停止链
                break

    def response(self, flow: http.HTTPFlow) -> None:
        """处理响应"""
        for interceptor in self.interceptors:
            if not interceptor.enabled:
                continue

            result = interceptor.response(flow)
            if result:  # 如果返回了修改后的 flow，停止链
                break
