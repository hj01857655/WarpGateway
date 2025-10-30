"""规则匹配工具"""

import re
from typing import List, Pattern
from enum import Enum


class RuleType(Enum):
    """规则类型"""
    EXACT = "exact"        # 精确匹配
    CONTAINS = "contains"  # 包含匹配
    REGEX = "regex"        # 正则匹配
    WILDCARD = "wildcard"  # 通配符匹配


class Rule:
    """匹配规则"""

    def __init__(self, pattern: str, rule_type: RuleType = RuleType.CONTAINS):
        self.pattern = pattern
        self.rule_type = rule_type
        self._compiled_pattern: Pattern = None

        if rule_type == RuleType.REGEX:
            self._compiled_pattern = re.compile(pattern)
        elif rule_type == RuleType.WILDCARD:
            # 转换通配符为正则表达式
            regex_pattern = pattern.replace(".", r"\.").replace("*", ".*").replace("?", ".")
            self._compiled_pattern = re.compile(regex_pattern)

    def match(self, text: str) -> bool:
        """匹配文本"""
        if self.rule_type == RuleType.EXACT:
            return text == self.pattern
        elif self.rule_type == RuleType.CONTAINS:
            return self.pattern in text
        elif self.rule_type in (RuleType.REGEX, RuleType.WILDCARD):
            return bool(self._compiled_pattern.search(text))
        return False

    def __repr__(self):
        return f"Rule(pattern={self.pattern}, type={self.rule_type.value})"


class RuleMatcher:
    """规则匹配器"""

    def __init__(self):
        self.rules: List[Rule] = []

    def add_rule(self, pattern: str, rule_type: RuleType = RuleType.CONTAINS):
        """添加规则"""
        rule = Rule(pattern, rule_type)
        self.rules.append(rule)
        return rule

    def add_rules(self, patterns: List[str], rule_type: RuleType = RuleType.CONTAINS):
        """批量添加规则"""
        for pattern in patterns:
            self.add_rule(pattern, rule_type)

    def match(self, text: str) -> bool:
        """检查是否匹配任一规则"""
        return any(rule.match(text) for rule in self.rules)

    def match_all(self, text: str) -> List[Rule]:
        """返回所有匹配的规则"""
        return [rule for rule in self.rules if rule.match(text)]

    def clear(self):
        """清空所有规则"""
        self.rules.clear()

    def __len__(self):
        return len(self.rules)

    def __repr__(self):
        return f"RuleMatcher(rules={len(self.rules)})"
