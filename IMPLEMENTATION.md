# WarpGateway 技术实现文档

## 🎯 项目目标

**核心需求：拦截和修改 Warp.dev 的 API 请求，实现多账号 Warp+ 流量轮换使用**

### 使用场景
- Warp.dev 是一个 AI 编程助手，使用 Warp+ 流量访问 AI 服务
- 单个账号流量有限，需要通过代理网关实现多账号轮换
- 拦截 Warp.dev 客户端的 API 请求，替换 Authorization Token
- 实现流量统计和账号自动切换

---

## 📋 实现路线图

### 阶段 1：基础代理框架 ✅
- [x] mitmproxy 基础代理服务器
- [x] 请求拦截器架构
- [x] 配置管理系统
- [x] 规则匹配引擎

### 阶段 2：Warp.dev API 分析 🔄
**关键任务：**
1. **抓包分析 Warp.dev 的 API 请求**
   - 使用代理拦截所有请求
   - 记录请求的 URL、Headers、Body
   - 识别哪些是 AI 服务相关的请求
   
2. **识别关键请求头**
   - 查找认证相关的 Header（如 `Authorization`、`X-API-Key` 等）
   - 记录其他可能重要的 Header

3. **分析请求体结构**
   - 记录请求体的 JSON 格式
   - 找出需要替换 Token 的位置

### 阶段 3：Token 管理系统 📝
**需要实现：**

#### 3.1 账号管理器
```python
# src/handlers/account_manager.py
class AccountManager:
    """Warp+ 账号管理器"""
    
    def __init__(self, accounts: list):
        self.accounts = accounts  # 账号列表
        self.current_index = 0
        self.usage_stats = {}  # 每个账号的使用统计
    
    def get_next_account(self):
        """轮换获取下一个账号"""
        account = self.accounts[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.accounts)
        return account
    
    def get_account_by_usage(self):
        """根据流量使用情况选择账号"""
        # 选择剩余流量最多的账号
        return min(self.accounts, key=lambda a: self.usage_stats.get(a['id'], 0))
```

#### 3.2 Token 替换拦截器
```python
# src/handlers/token_replacer.py
class TokenReplacer(BaseInterceptor):
    """Token 替换拦截器"""
    
    def __init__(self, account_manager, target_domain):
        super().__init__("TokenReplacer")
        self.account_manager = account_manager
        self.target_domain = target_domain  # 从配置读取目标域名
    
    def request(self, flow: http.HTTPFlow):
        """替换请求中的 Authorization Token"""
        # 识别目标 API 请求（域名从配置中获取）
        if self.target_domain in flow.request.pretty_url:
            # 获取当前账号
            account = self.account_manager.get_next_account()
            
            # 替换 Authorization Header（具体 Header 名称需要抓包确认）
            flow.request.headers["Authorization"] = f"Bearer {account['token']}"
            
            logger.info(f"🔄 使用账号: {account['name']} (剩余流量: {account['quota']}GB)")
        
        return None
```

### 阶段 4：流量统计和自动切换 📊

#### 4.1 流量监控
```python
class UsageTracker(BaseInterceptor):
    """流量使用追踪器"""
    
    def __init__(self, account_manager):
        super().__init__("UsageTracker")
        self.account_manager = account_manager
    
    def request(self, flow: http.HTTPFlow):
        """记录请求大小"""
        request_size = len(flow.request.content or b"")
        self.account_manager.add_usage(request_size)
        return None
    
    def response(self, flow: http.HTTPFlow):
        """记录响应大小"""
        if flow.response:
            response_size = len(flow.response.content or b"")
            self.account_manager.add_usage(response_size)
        return None
```

#### 4.2 账号自动切换策略
- **按请求数切换**：每 N 个请求切换一次账号
- **按流量切换**：当前账号流量用完后切换
- **按时间切换**：每隔 T 分钟切换账号
- **智能切换**：根据账号剩余流量动态选择

### 阶段 5：配置文件结构 ⚙️

```yaml
# config.yaml
proxy:
  host: "127.0.0.1"
  port: 8080
  cert_dir: "~/.mitmproxy"

# Warp+ 账号配置
accounts:
  - name: "账号1"
    token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    quota: 10  # GB
    priority: 1
  
  - name: "账号2"
    token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    quota: 15
    priority: 2

# 账号轮换策略
rotation:
  strategy: "smart"  # round_robin | by_usage | by_time | smart
  switch_after_requests: 100  # 每 N 个请求切换
  check_usage_interval: 60  # 每分钟检查一次流量

# API 拦截规则
warp_api:
  target_domain: ""  # 通过抓包分析后填写实际域名
  intercept_paths: []  # 通过抓包分析后添加需要拦截的路径
  auth_header: "Authorization"  # 通过抓包分析后确认实际的认证 Header 名称

# 日志和统计
logging:
  level: "INFO"
  file: "logs/warp_gateway.log"
  
stats:
  enabled: true
  save_interval: 300  # 每 5 分钟保存一次统计
  output_file: "logs/stats.json"
```

### 阶段 6：GUI 界面增强 🖥️

#### 6.1 系统托盘功能
- [x] 启动/停止代理
- [x] 查看状态
- [ ] **账号管理面板**
  - 显示所有账号及剩余流量
  - 手动切换账号
  - 添加/删除账号
- [ ] **实时流量监控**
  - 当前使用的账号
  - 实时请求速率
  - 流量使用图表

#### 6.2 Web 控制面板（可选）
```python
# src/gui/web_ui.py
from flask import Flask, render_template, jsonify

app = Flask(__name__)

@app.route('/')
def dashboard():
    """主面板"""
    return render_template('dashboard.html')

@app.route('/api/accounts')
def get_accounts():
    """获取账号列表"""
    return jsonify(account_manager.get_all_accounts())

@app.route('/api/stats')
def get_stats():
    """获取统计数据"""
    return jsonify(stats_manager.get_stats())
```

---

## 🔧 关键技术点

### 1. HTTPS 拦截
Warp.dev API 使用 HTTPS，需要安装 mitmproxy 证书：

```bash
# 生成证书
mitmdump

# 安装证书（Windows）
# 1. 打开 %USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.cer
# 2. 安装到"受信任的根证书颁发机构"

# 或使用代码自动安装
python -m src.utils.install_cert
```

### 2. 请求修改时机
```python
def request(self, flow: http.HTTPFlow):
    # 在请求发送前修改
    # 修改 Headers
    flow.request.headers["Authorization"] = new_token
    
    # 修改 Body（如果需要）
    if flow.request.content:
        body = json.loads(flow.request.content)
        body["user_id"] = new_user_id
        flow.request.content = json.dumps(body).encode()
    
    return None  # 继续处理
```

### 3. 流式响应处理
Warp.dev 的 AI 响应是流式的（Server-Sent Events），需要特殊处理：

```python
def response(self, flow: http.HTTPFlow):
    if flow.response and "text/event-stream" in flow.response.headers.get("content-type", ""):
        # 启用流式传输
        flow.response.stream = True
        logger.info("🌊 启用 SSE 流式响应")
    return None
```

### 4. 错误处理和重试
```python
class RetryHandler(BaseInterceptor):
    """请求重试处理器"""
    
    def response(self, flow: http.HTTPFlow):
        if flow.response and flow.response.status_code == 429:
            # Token 流量用尽，切换账号重试
            logger.warning("⚠️ 当前账号流量不足，切换账号")
            account_manager.mark_quota_exceeded()
            
            # 使用新账号重试请求
            new_account = account_manager.get_next_account()
            flow.request.headers["Authorization"] = f"Bearer {new_account['token']}"
            # TODO: 重新发送请求
        
        return None
```

---

## 📝 开发任务清单

### 立即任务（本次实现）
1. [ ] 完善 `AccountManager` 类
2. [ ] 实现 `TokenReplacer` 拦截器
3. [ ] 实现 `UsageTracker` 流量统计
4. [ ] 更新 `config.yaml` 支持账号配置
5. [ ] 在 GUI 中显示账号列表和流量

### 短期任务
1. [ ] 抓包分析 Warp.dev 真实 API
2. [ ] 实现账号自动切换逻辑
3. [ ] 添加流量监控面板
4. [ ] 实现请求失败重试

### 长期任务
1. [ ] Web 控制面板
2. [ ] 账号健康检查
3. [ ] 自动获取新账号（如果有 API）
4. [ ] 分布式部署支持

---

## 🚀 快速开始指南

### 1. 准备账号
收集多个 Warp+ 账号的 Token，添加到 `config.yaml`

### 2. 安装证书
```bash
# 启动一次代理生成证书
python -m src.proxy

# 安装 mitmproxy 证书
# Windows: ~/.mitmproxy/mitmproxy-ca-cert.cer
```

### 3. 配置 Warp.dev 客户端
将 Warp.dev 设置为使用本地代理：
- HTTP Proxy: `127.0.0.1:8080`
- HTTPS Proxy: `127.0.0.1:8080`

### 4. 启动网关
```bash
# 命令行模式
python -m src.proxy

# GUI 模式
python run_gui.py
# 或双击：启动WarpGateway.bat
```

### 5. 验证功能
- 在 Warp.dev 中使用 AI 功能
- 查看代理日志，确认 Token 替换成功
- 观察账号轮换是否正常

---

## 🐛 常见问题

### Q1: 为什么拦截不到 Warp.dev 的请求？
- 检查 Warp.dev 是否配置了代理
- 确认 mitmproxy 证书已安装
- 查看代理日志是否有错误

### Q2: Token 替换后请求失败？
- 验证 Token 格式是否正确
- 检查 API 请求结构是否匹配
- 查看 Warp.dev 的错误响应

### Q3: 如何获取 Warp+ Token？
- 登录 Warp.dev 账号
- 打开浏览器开发者工具（F12）
- 查看网络请求中的 `Authorization` Header

---

## 📚 相关资源

- [mitmproxy 文档](https://docs.mitmproxy.org/)
- [PySide6 文档](https://doc.qt.io/qtforpython/)
- [HTTP 代理原理](https://en.wikipedia.org/wiki/Proxy_server)

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

如果你有更好的实现思路或发现了 Bug，请随时联系。

---

**现在的重点是：先抓包分析 Warp.dev 的真实 API 请求，然后实现 Token 替换功能！**
