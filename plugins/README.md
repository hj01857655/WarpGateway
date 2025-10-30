# 插件目录

这里可以放置自定义的插件和处理器。

## 创建插件

1. 继承 `BaseInterceptor` 类
2. 实现 `request()` 和 `response()` 方法
3. 在 `proxy.py` 中注册插件

## 示例

```python
# plugins/my_plugin.py
from src.core.interceptor import BaseInterceptor
from mitmproxy import http
from typing import Optional

class MyPlugin(BaseInterceptor):
    def __init__(self):
        super().__init__("MyPlugin")
        
    def request(self, flow: http.HTTPFlow) -> Optional[http.HTTPFlow]:
        # 自定义请求处理逻辑
        print(f"Processing: {flow.request.url}")
        return None
        
    def response(self, flow: http.HTTPFlow) -> Optional[http.HTTPFlow]:
        # 自定义响应处理逻辑
        return None
```

## 注册插件

在 `src/core/proxy.py` 的 `ProxyServer.setup_handlers()` 中添加：

```python
from plugins.my_plugin import MyPlugin

def setup_handlers(self):
    # ... 现有处理器 ...
    
    # 添加自定义插件
    my_plugin = MyPlugin()
    self.chain.add(my_plugin)
```
