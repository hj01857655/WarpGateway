# WarpGateway

基于 mitmproxy 的 Warp.dev 请求拦截代理网关。

## 功能特性

- 🔍 拦截 Warp.dev 相关请求
- ✅ 可配置的请求放行/拦截规则
- 📝 请求日志记录（JSON Lines 格式）
- 📊 实时请求统计分析
- 🔗 拦截器链架构，易于扩展
- 🎯 支持多种规则匹配方式（精确/包含/正则/通配符）
- ⚙️ 灵活的配置管理

## 安装

```bash
pip install -e .
```

## 使用方法

### 基本使用

```bash
python -m src.proxy
```

### 使用自定义配置

```bash
python -m src.proxy --config config.yaml
```

### 配置 Warp 客户端

将 Warp 客户端代理设置为：
- 主机: `localhost`
- 端口: `8080`（默认）

## 配置文件

在 `config.yaml` 中配置拦截规则：

```yaml
proxy:
  host: "0.0.0.0"
  port: 8080

rules:
  # 拦截规则
  block:
    - "api.warp.dev/v1/billing"
  
  # 放行规则
  allow:
    - "api.warp.dev/v1/auth"
  
  # 记录但不拦截
  log_only:
    - "api.warp.dev/v1/analytics"

logging:
  level: "INFO"
  file: "warp_gateway.log"
```

## 项目结构

```
WarpGateway/
├── src/
│   ├── core/              # 核心功能
│   │   ├── config.py      # 配置管理
│   │   ├── interceptor.py # 拦截器基类和链
│   │   └── proxy.py       # 代理服务器
│   ├── handlers/          # 请求处理器
│   │   ├── warp.py        # Warp 专用处理器
│   │   ├── logger.py      # 日志处理器
│   │   └── stats.py       # 统计处理器
│   └── utils/             # 工具模块
│       └── rules.py       # 规则匹配工具
├── plugins/               # 插件目录
├── logs/                  # 日志目录
├── config.yaml
└── README.md
```

## 开发

### 自定义处理器

继承 `BaseInterceptor` 类即可创建自定义处理器：

```python
from src.core.interceptor import BaseInterceptor
from mitmproxy import http

class MyHandler(BaseInterceptor):
    def __init__(self):
        super().__init__("MyHandler")
    
    def request(self, flow: http.HTTPFlow):
        # 处理请求
        return None
    
    def response(self, flow: http.HTTPFlow):
        # 处理响应
        return None
```

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 代码格式化

```bash
black .
ruff check .
```

## 许可证

MIT License
