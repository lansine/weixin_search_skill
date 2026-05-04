# weixin_search_skill

微信 / 腾讯内容搜索 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skill。

多引擎并行搜索 + Playwright 浏览器 + Tavily 深度调研，覆盖 qq.com 全域内容。

## 特性

- **多引擎并行搜索** — 搜狗微信 + 百度 + Google，异步并行（每个引擎独立 tab），结果自动去重
- **Playwright 浏览器** — 真实浏览器环境，绕过反爬机制
- **同会话链接解析** — 搜索阶段即解析搜狗重定向，内容获取零障碍
- **通用内容提取** — 微信公众号、腾讯新闻等多种页面结构自动适配，未知页面 fallback 到 body 主体
- **腾讯全域覆盖** — `site:qq.com`，不仅限于微信公众号
- **多层内容兜底** — Playwright → Tavily Extract → web.archive.org 三层保障
- **深度调研模式** — Tavily Search + Research + Crawl 多源综合分析
- **时间过滤** — 支持 day / week / month / year 范围限定

## 什么是 Claude Code Skill

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) 是 Anthropic 推出的 AI 编程助手，支持命令行、桌面应用和 IDE 插件。

**Skill** 是 Claude Code 的扩展机制 —— 通过一个 `SKILL.md` 文件定义一组能力（搜索、分析、调研等），注册后可以在 Claude Code 中用 `/skill-name` 触发。Skill 不是 MCP server，不需要启动后台服务，它本质上是一份结构化的指令，告诉 Claude 如何组合工具来完成特定任务。

本项目就是一个 Skill：注册后在 Claude Code 中输入 `/weixin-search AI大模型`，Claude 会自动调用本地 Playwright 搜索引擎 + Tavily API，完成搜索、内容获取、摘要分析的完整流程。

## 安装

### 前置条件

- [uv](https://docs.astral.sh/uv/) — Python 包管理工具
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — Anthropic AI 编程助手

### Step 1: 克隆项目

```bash
git clone https://github.com/lansine/weixin_search_skill.git
cd weixin_search_skill
```

### Step 2: 安装 CLI 工具

```bash
uv tool install .
playwright install chromium
```

安装后 `weixin-search` 命令全局可用，可以先验证一下：

```bash
weixin-search search "测试" --pages 1 --engines sogou
```

### Step 3: 注册为 Claude Code Skill

```bash
mkdir -p ~/.claude/skills/weixin-search
ln -s "$(pwd)/SKILL.md" ~/.claude/skills/weixin-search/SKILL.md
```

注册后重启 Claude Code，输入 `/weixin-search` 即可看到技能提示。

### Step 4: 配置 Tavily MCP（可选）

深度调研模式和搜索兜底需要 [Tavily](https://tavily.com/) API。配置方式：

```bash
# 在 Claude Code 中运行
/mcp add tavily -- npx -y @anthropic-ai/tavily-mcp@latest
```

或手动编辑 `~/.claude/mcp.json`：

```json
{
  "mcpServers": {
    "tavily": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/tavily-mcp@latest"],
      "env": {
        "TAVILY_API_KEY": "your-api-key"
      }
    }
  }
}
```

不配置 Tavily 也能正常使用快速搜索功能，只是无法使用 `--deep` 深度调研模式。

## 在 Claude Code 中使用

### 快速搜索

输入 `/weixin-search` 加关键词，Claude 会自动搜索并展示结果表格：

```
/weixin-search AI大模型
```

Claude 返回结果表格后，回复文章序号即可查看全文内容。

### 更多用法

```
/weixin-search --pages 5 新能源汽车        # 每个引擎搜 5 页
/weixin-search --time week Claude Code     # 只看最近一周
/weixin-search --deep AI大模型发展趋势      # 深度调研（需要 Tavily）
/weixin-search --pages 3 --time month 充电桩  # 参数可组合
```

### 工作流示例

**快速搜索 → 阅读文章：**

```
你: /weixin-search 新能源汽车补贴政策
Claude: 找到 15 篇文章：
  | # | 标题 | 发布时间 | 来源 |
  |---|------|---------|------|
  | 1 | 2025年新能源汽车补贴政策全解读 | 2025-04-28 | sogou |
  | 2 | ... | ... | ... |
  需要查看哪篇的详细内容？输入序号即可。

你: 1
Claude: [获取文章全文并做摘要分析]
```

**深度调研：**

```
你: /weixin-search --deep 固态电池技术路线
Claude: [并行执行搜狗+百度+Google+Tavily搜索，阅读关键文章，输出结构化调研报告]
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `<关键词>` | 必填 | 搜索关键词 |
| `--pages N` | 3 / 深度 5 | 每个引擎搜索页数 |
| `--time RANGE` | 无限制 | `day` / `week` / `month` / `year` |
| `--deep` | 关闭 | 启用深度调研模式（需要 Tavily） |

### 搜索引擎

| 引擎 | 特点 | 快速模式 | 深度模式 |
|------|------|:--------:|:--------:|
| 搜狗微信 | 微信独家索引，覆盖最全 | ✓ | ✓ |
| 百度 | `site:qq.com`，腾讯全域覆盖 | ✓ | ✓ |
| Google | 长尾 / 冷门文章 | | ✓ |
| Tavily Search | AI 搜索，qq.com 域名限定 | 兜底 | ✓ |
| Tavily Research | 多源综合调研 | | ✓ |

## 独立使用（不依赖 Claude Code）

安装后也可以直接命令行运行，适合脚本集成或调试：

```bash
# 搜索（输出 JSON）
weixin-search search "AI大模型" --pages 3 --engines sogou,baidu

# 获取文章内容（输出纯文本）
weixin-search content "<文章URL>"

# 三引擎搜索
weixin-search search "新能源" --pages 2 --engines sogou,baidu,google
```

## 架构说明

```
用户输入 /weixin-search
       │
       ▼
   SKILL.md（流程编排）
       │
       ├─ weixin-search CLI（Playwright 搜索 + 内容获取）
       │    ├─ 搜狗微信  ─┐
       │    ├─ 百度      ─┼─ 异步并行 → 去重 → 结果表格
       │    └─ Google    ─┘
       │
       └─ Tavily MCP（可选）
            ├─ tavily_search    ─ 兜底搜索 / 深度补充
            ├─ tavily_extract   ─ 内容获取兜底
            ├─ tavily_research  ─ 综合调研
            └─ tavily_crawl     ─ 发现更多内容
```

## 致谢

灵感来源于 [weixin_search_mcp](https://github.com/woniu9524/weixin_search_mcp) 项目。本项目在其基础上完全重写，采用不同的架构和技术方案。

## License

MIT
