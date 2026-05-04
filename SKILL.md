---
name: weixin-search
description: 搜索腾讯体系内容（微信公众号、腾讯新闻等 qq.com）。多引擎（搜狗+百度+Google）+ Tavily 深度调研。当用户提到"微信搜索"、"公众号文章"、"搜一下微信"、"腾讯"等关键词时使用。
---

# 微信 / 腾讯内容搜索

多引擎搜索腾讯体系内容（微信公众号、腾讯新闻等 qq.com 域名），Playwright 浏览器获取真实链接和内容，支持深度调研。

## 用法

```
/weixin-search <关键词>
/weixin-search --pages 3 AI大模型
/weixin-search --time week 新能源汽车
/weixin-search --deep Claude Code 最新功能
```

## 参数解析

用户输入：`{{ input }}`

| 参数 | 默认值 | 说明 | 示例 |
|------|--------|------|------|
| `<关键词>` | （必填） | 搜索关键词 | `AI大模型` |
| `--pages N` | 普通 `3` / 深度 `5` | 每个引擎的搜索页数 | `--pages 5` |
| `--time RANGE` | 无限制 | 时间范围：`day`/`week`/`month`/`year` | `--time week` |
| `--deep` | 关闭 | 启用深度调研模式 | `--deep` |

解析规则：
- **无参数**：提示用户输入搜索关键词
- **仅关键词**：`/weixin-search AI大模型` → 快速搜索（搜狗+百度）
- **指定页数**：`/weixin-search --pages 5 AI大模型` → 每个引擎搜 5 页
- **指定时间**：`/weixin-search --time week 新能源` → 只看最近一周
- **深度调研**：`/weixin-search --deep AI大模型` → 全引擎 + Tavily 调研
- 参数可组合：`/weixin-search --pages 2 --time month AI大模型`

## 搜索引擎说明

| 引擎 | 特点 | 何时使用 |
|------|------|---------|
| **搜狗微信** | 微信独家索引，覆盖最全，结果最精准 | 始终使用（主力） |
| **百度** | 最大中文索引，`site:qq.com` 覆盖腾讯全域 | 始终使用（补充） |
| **Google** | 国际视角，能找到长尾/冷门文章 | 深度调研模式使用 |
| **Tavily Search** | AI 搜索引擎，直接返回 qq.com 域名链接 | 深度调研 + 兜底 |
| **Tavily Research** | 多源综合调研，不限微信 | 深度调研模式使用 |

## 执行流程

### 模式一：快速搜索（默认）

#### Step 1: 多引擎搜索

```bash
weixin-search search "<关键词>" --pages <N> --engines sogou,baidu
```

- `--pages` 取用户指定值，未指定则默认 `3`
- 使用 Playwright 无头浏览器同时搜索搜狗微信和百度
- 输出 JSON 数组，每条包含 `title`、`link`、`real_url`、`publish_time`、`source`
- 结果自动按标题去重

#### Step 1.5: 时间过滤

如果用户指定了 `--time`，对搜索结果按 `publish_time` 过滤：
- `day`：只保留最近 24 小时
- `week`：只保留最近 7 天
- `month`：只保留最近 30 天
- `year`：只保留最近 365 天

#### Step 2: 判断搜索结果

- **有结果**：跳到 Step 3
- **无结果**：使用 Tavily 兜底（见 Fallback 章节）

#### Step 3: 展示结果

以表格形式展示搜索结果：

| # | 标题 | 发布时间 | 来源 |
|---|------|---------|------|
| 1 | 文章标题 | 2025-05-04 | sogou |
| 2 | 文章标题 | 2025-05-03 | baidu |

然后询问用户：「找到 N 篇文章，需要查看哪篇的详细内容？输入序号即可。」

#### Step 4: 获取文章内容

当用户选择某篇文章后，使用 Playwright 获取正文：

```bash
weixin-search content "<url>"
```

- `<url>` 优先使用 `real_url`，如为空则使用 `link`
- 脚本自动处理各种 URL 类型：
  - `qq.com` 域名链接：直接获取（微信公众号、腾讯新闻等）
  - 搜狗/百度重定向链接：自动解析跳转后获取
  - 文章已删除：自动尝试 web.archive.org 存档
- 如果 Playwright 获取失败，fallback 到 Tavily Extract：

使用 `mcp__tavily__tavily_extract` 工具：
- `urls`: `["<real_url>"]`
- `extract_depth`: `"advanced"`
- `query`: 用户原始搜索关键词
- `format`: `"markdown"`

获取内容后，为用户做摘要分析，重点提取与搜索关键词相关的信息。

### 模式二：深度调研（--deep）

当用户使用 `--deep` 参数时，执行全面调研：

#### Step 1: 全引擎并行搜索

同时执行：

1. **Playwright 多引擎搜索**（搜狗 + 百度 + Google）：
```bash
weixin-search search "<关键词>" --pages <N> --engines sogou,baidu,google
```
- `--pages` 默认 `5`

2. **Tavily Search**（微信域名限定）：
使用 `mcp__tavily__tavily_search` 工具：
- `query`: 用户关键词
- `search_depth`: `"advanced"`
- `include_domains`: `["qq.com"]`
- `max_results`: 20
- `time_range`: 取用户 `--time` 值，未指定则默认 `"month"`

3. **Tavily Research**（综合调研，不限微信）：
使用 `mcp__tavily__tavily_research` 工具：
- `input`: `"调研以下主题，重点关注微信公众号和腾讯新闻的观点和数据：<关键词>"`
- `model`: `"pro"`

合并所有搜索结果，按标题去重。

#### Step 2: 深入阅读关键文章

从结果中选择最相关的 3-5 篇文章，获取全文：

- 有 `real_url` 的文章：使用 Playwright 本地获取
- 仅有 Tavily URL 的文章：使用 `mcp__tavily__tavily_extract` 获取
  - `urls`: 选取的文章 URL 列表
  - `extract_depth`: `"advanced"`
  - `query`: 用户关键词

#### Step 3: 发现更多内容（可选）

如果某篇文章质量很高，使用 `mcp__tavily__tavily_crawl` 从该文章出发发现同一公众号的更多文章：
- `url`: 高质量文章的 URL
- `instructions`: `"查找同一公众号下与<关键词>相关的其他文章"`
- `max_depth`: 2
- `limit`: 10
- `select_domains`: `["qq.com"]`

#### Step 4: 输出调研报告

整合所有信息，输出结构化报告：
- 主题概述
- 核心观点（按文章来源标注）
- 关键数据/事实
- 趋势/结论
- 参考文章列表（标题 + 链接）

## Fallback: Tavily 搜索兜底

当 Playwright 搜索返回空结果时：

使用 `mcp__tavily__tavily_search` 工具：
- `query`: 用户关键词
- `include_domains`: `["qq.com"]`
- `search_depth`: `"advanced"`
- `max_results`: `--pages` × 10（默认 30）
- `time_range`: 取用户 `--time` 值（如有）

将结果转换为相同的表格格式展示。

## 注意事项

- 搜索使用 Playwright 无头浏览器，搜狗+百度双引擎默认开启，深度模式加入 Google
- 多引擎并行搜索（每个引擎独立 tab），搜索耗时约 15-30 秒
- 百度结果通过 `mu` 属性直接获取真实 qq.com 链接，无需额外跳转
- 搜狗/百度重定向链接在获取内容时自动解析，无需手动处理
- 已删除的文章会自动尝试 web.archive.org 存档获取
- 深度调研模式叠加 Tavily 多源搜索 + Research，覆盖面最广但耗时更长
