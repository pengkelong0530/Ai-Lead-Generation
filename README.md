# AI 海外获客 Agent

基于 LangChain 的 AI 海外获客智能体。自动完成目标企业搜索、ICP 筛选、评分、信息采集、邮件生成到数据持久化的完整获客流程。

## 快速启动

### 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 3. 运行
streamlit run main.py
```

### Demo 模式（无需 API Key）

```bash
python main.py --demo
```

## 部署到 Streamlit Cloud

### 前置准备

| 项目 | 获取方式 |
|---|---|
| Tavily API Key | https://tavily.com 注册 Maker 计划（免费 1000 次/月） |
| OpenAI / 兼容 API Key | 你的 opencode go 或其他兼容密钥 |

### 步骤

1. **Fork 或 Push 代码到 GitHub**

2. **登录 Streamlit Cloud**
   - 访问 https://streamlit.io/cloud
   - 用 GitHub 账号登录
   - 点击 "New app"

3. **配置部署**
   - Repository: 选择你的仓库
   - Branch: `main`
   - Main file path: `main.py`
   - 点击 "Advanced settings"

4. **设置 Secrets（环境变量）**
   ```
   OPENAI_API_KEY = sk-你的密钥
   OPENAI_BASE_URL = https://你的兼容地址/v1  (可选)
   TAVILY_API_KEY = tvly-你的密钥
   DB_TYPE = sqlite
   ```

5. **部署**
   - 点击 "Deploy"
   - 等待 2-3 分钟
   - 获得 `https://xxx.streamlit.app` 链接

6. **发送给面试官** - 链接可以直接在手机和电脑上打开使用

## 项目结构

```
├── main.py              # 入口
├── config.py            # 配置
├── agent/               # Agent 编排层
├── chains/              # LangChain 链
├── tools/               # 工具层（搜索/爬取）
├── models/              # 数据模型
├── db/                  # 数据库（MySQL + SQLite）
├── memory/              # 记忆持久化
├── ui/                  # 界面
└── demo/                # 演示模式
```

## 环境变量说明

| 变量 | 必填 | 说明 |
|---|---|---|
| `OPENAI_API_KEY` | 是 | LLM API Key |
| `OPENAI_BASE_URL` | 否 | 兼容 API 的基础地址 |
| `TAVILY_API_KEY` | 是 | 搜索引擎 Key |
| `DB_TYPE` | 否 | `auto` / `sqlite` / `mysql` |