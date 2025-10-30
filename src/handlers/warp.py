"""Warp.dev 请求处理器"""

import logging
from mitmproxy import http
from typing import Optional
from ..core.interceptor import BaseInterceptor
from ..utils.rules import RuleMatcher, RuleType

logger = logging.getLogger(__name__)


class WarpHandler(BaseInterceptor):
    """Warp 请求处理器"""

    def __init__(self, config):
        super().__init__("WarpHandler")
        self.config = config

        # 初始化规则匹配器
        self.block_matcher = RuleMatcher()
        self.allow_matcher = RuleMatcher()
        self.log_only_matcher = RuleMatcher()

        # 加载规则
        self._load_rules()

    def _load_rules(self):
        """加载规则"""
        # 默认使用包含匹配，可以根据配置使用其他类型
        self.block_matcher.add_rules(self.config.block_rules, RuleType.CONTAINS)
        self.allow_matcher.add_rules(self.config.allow_rules, RuleType.CONTAINS)
        self.log_only_matcher.add_rules(self.config.log_only_rules, RuleType.CONTAINS)

        logger.info(f"📋 Loaded {len(self.block_matcher)} block rules")
        logger.info(f"📋 Loaded {len(self.allow_matcher)} allow rules")
        logger.info(f"📋 Loaded {len(self.log_only_matcher)} log_only rules")

    def request(self, flow: http.HTTPFlow) -> Optional[http.HTTPFlow]:
        """处理请求"""
        url = flow.request.pretty_url
        method = flow.request.method
        path = flow.request.path

        # 检查拦截规则
        if self.block_matcher.match(url):
            logger.warning(f"🚫 BLOCKED: {method} {url}")
            flow.response = http.Response.make(
                403,
                b"Request blocked by WarpGateway",
                {"Content-Type": "text/plain; charset=utf-8"},
            )
            return flow  # 返回修改后的 flow，阻止后续处理

        # 启用流式响应（适用于 AI 流式输出）
        for stream_path in self.config.streaming_paths:
            if stream_path in path:
                flow.response = http.Response.make(200)
                flow.response.stream = True
                logger.info(f"🌊 STREAM ENABLED: {method} {url}")
                break

        # 检查放行规则
        if self.allow_matcher.match(url):
            logger.info(f"✅ ALLOWED: {method} {url}")
            return None

        # 检查仅记录规则
        if self.log_only_matcher.match(url):
            logger.info(f"📝 LOG_ONLY: {method} {url}")
            return None

        # 其他请求正常通过
        logger.debug(f"➡️  PASS: {method} {url}")
        return None

    def response(self, flow: http.HTTPFlow) -> Optional[http.HTTPFlow]:
        """处理响应"""
        if flow.response:
            url = flow.request.pretty_url
            status = flow.response.status_code
            logger.debug(f"⬅️  RESPONSE: {url} [{status}]")
        return None

    def add_block_rule(self, pattern: str, rule_type: RuleType = RuleType.CONTAINS):
        """动态添加拦截规则"""
        self.block_matcher.add_rule(pattern, rule_type)
        logger.info(f"➕ Added block rule: {pattern}")

    def add_allow_rule(self, pattern: str, rule_type: RuleType = RuleType.CONTAINS):
        """动态添加放行规则"""
        self.allow_matcher.add_rule(pattern, rule_type)
        logger.info(f"➕ Added allow rule: {pattern}")
