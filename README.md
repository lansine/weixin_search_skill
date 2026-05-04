# weixin_search_skill

微信 / 腾讯内容搜索 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skill。

多引擎搜索 + Playwright 浏览器 + Tavily 深度调研，覆盖 qq.com 全域内容。

## 特性

- **多引擎搜索** — 搜狗微信（独家索引）+ 百度 + Google，结果自动去重
- **Playwright 浏览器** — 真实浏览器环境，绕过反爬机制
- **同会话链接解析** — 搜索阶段即解析搜狗重定向，内容获取零障碍
- **腾讯全域覆盖** — `site:qq.com`，不仅限于微信公众号
- **多层内容提取** — Playwright → Tavily Extract → web.archive.org 三层兜底
- **深度调研模式** — Tavily Search + Research + Crawl 多源综合分析
- **时间过滤** — 支持 day / week / month / year 范围限定

## 安装

### 1. 克隆项目

```bash
git clone https://github.com/lansine/weixin_search_skill.git
cd weixin_search_skill
```

### 2. 安装依赖

```bash
uv sync
uv run playwright install chromium
```

### 3. 注册为 Claude Code Skill

```bash
mkdir -p ~/.claude/skills/weixin-search
ln -s "$(pwd)/SKILL.md" ~/.claude/skills/weixin-search/SKILL.md
```

### 4. 配置 Tavily MCP（可选，深度调研需要）

在 Claude Code 中添加 Tavily MCP server，用于深度调研模式和搜索兜底。

## 用法

在 Claude Code 中使用：

```
/weixin-search AI大模型
/weixin-search --pages 5 新能源汽车
/weixin-search --time week Claude Code
/weixin-search --deep AI大模型发展趋势
```

### 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `<关键词>` | 必填 | 搜索关键词 |
| `--pages N` | 3 / 深度 5 | 每个引擎搜索页数 |
| `--time RANGE` | 无限制 | `day` / `week` / `month` / `year` |
| `--deep` | 关闭 | 启用深度调研模式 |

### 搜索引擎

| 引擎 | 特点 | 快速模式 | 深度模式 |
|------|------|:--------:|:--------:|
| 搜狗微信 | 微信独家索引，覆盖最全 | ✓ | ✓ |
| 百度 | `site:qq.com`，腾讯全域覆盖 | ✓ | ✓ |
| Google | 长尾 / 冷门文章 | | ✓ |
| Tavily Search | AI 搜索，qq.com 域名限定 | 兜底 | ✓ |
| Tavily Research | 多源综合调研 | | ✓ |

## 独立使用（不依赖 Claude Code）

脚本也可以直接命令行运行：

```bash
# 搜索
uv run python3 weixin_search.py search "AI大模型" --pages 3 --engines sogou,baidu

# 获取文章内容
uv run python3 weixin_search.py content "<文章URL>"
```

## 致谢

灵感来源于 [weixin_search_mcp](https://github.com/woniu9524/weixin_search_mcp) 项目。本项目在其基础上完全重写，采用不同的架构和技术方案。

## License

MIT
