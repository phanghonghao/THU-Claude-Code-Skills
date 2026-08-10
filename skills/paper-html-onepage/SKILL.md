---
name: paper-html-onepage
description: >
  从关键词/URL/PDF 自动检索论文（arXiv 优先），提取全文并生成单页 A4 风格 HTML 总结。
  网络层带 requests -> curl 自动降级，配合 /web-search-fallback，MCP 失效（429/限流/不可用）时仍可用。
  适用于“论文 -> 可读网页总结”场景。
---

# Paper to One-page HTML Skill

## 功能

- 输入关键词 / arXiv / PDF URL / 本地 PDF，自动获取论文
- 下载对应 PDF
- 按 `pdf-reader` 同款方式提取全文（PyMuPDF）
- 先生成完整全文 HTML（逐页文本，默认作为中间产物生成后删除）
- 再基于全文做一轮总结，生成单页 A4 风格 HTML（和 DreamDojo summary 类似的卡片化布局）
- 无论输入是 `--query`、`--url` 还是外部 `--pdf <path>`，默认都会在最终输出目录保留一份本地源 PDF，并尽量与主输出同名

## 网络与降级（不依赖 MCP）

本 skill 的全部网络操作（arXiv 检索、按 ID 取元数据、下载 PDF）都带 **requests -> curl 自动降级**，对应 `/web-search-fallback` 的 Route 1（arXiv API）和 Route 4（直接 curl 抓取/下载）。降级链：

1. 优先用 Python `requests`
2. `requests` 不可用 / 抛异常（被限流、429、代理或 MCP web 工具失效）-> 自动改用系统 `curl`
3. `curl` 也不可用 -> 打印 `[WARN]` 并退出

因此即使 `requests` 没装好、或 MCP `web_search` / `webReader` 返回 429 / `Limit Exhausted`，本 skill 仍能**独立**完成检索 + 下载 + 渲染，不会被 MCP 失效卡住。

也可把 `/web-search-fallback` 当前置：先用它的 Route 1/4 拿到 arXiv ID 或把 PDF 下到本地，再用 `--pdf <path>` 或 `--url <url>` 喂给本 skill。

## 使用方式

在任意目录执行（建议在你的项目目录）：

```powershell
python "<LOCAL_USER>\.codex\skills\paper-html-onepage\scripts\paper_to_onepage_html.py" --query "DreamDojo world model" --out "<OUTPUT_DIR>\dreamdojo_onepage.html"
```

直接传论文 URL（arXiv abs/pdf 或任意 PDF 直链，推荐用于已知论文）：

```powershell
python "<LOCAL_USER>\.codex\skills\paper-html-onepage\scripts\paper_to_onepage_html.py" --url "https://arxiv.org/pdf/2602.23843" --out "<OUTPUT_DIR>\papers\20_locomotion\omni_xtreme\OmniXtreme.html"
```

也可以不传 `--out`，脚本会自动从论文标题/关键词命名，优先提取类似 `DreamDojo`、`DreamZero`、`AMP` 这类关键词；如果没有明显关键词，再退回到标题前几项内容生成文件名。若关键词重名，脚本会自动补一个标题后缀避免覆盖旧文件。

对比模式（默认彩色简约单页，Method/Data 导向）：

```powershell
python "<SKILL_ROOT>\scripts\paper_to_onepage_html.py" --compare --items "<INPUT_DIR>\DreamDojo_summary.html" "<INPUT_DIR>\DreamZero_summary.html" --out "<OUTPUT_DIR>\DreamDojo_vs_DreamZero_compare_colorful.html"
```

如果不传 `--items`，脚本会交互式询问文件路径（用 `|` 分隔），不需要硬编码。

可选参数：

- `--query "..."`：按关键词检索 arXiv
- `--url <url>`：直接传论文 URL（arXiv abs/pdf 或直链 PDF），自动下载并生成 HTML；网络层带 curl 降级
- `--pdf <path>`：跳过检索/下载，直接读取本地 PDF 生成 HTML
- `--max-pages 60`：最多读取多少页（默认 80）
- `--pick 1`：检索结果中选择第几个（默认第 1 个）
- `--keep-pdf`：显式保留下载的 PDF；现在是默认行为，主要用于兼容旧命令
- `--no-keep-pdf`：不保留 `--url` / `--query` 模式下载下来的本地 PDF，恢复旧的临时文件行为
- `--keep-fulltext-html`：保留中间生成的 `*_fulltext.html`（默认生成后删除）
- `--reflection <path>`：把本地 Markdown/TXT 读后感整理成一页反思页 HTML，尽量保留原内容，并自动嵌入 Markdown 图片
- `--out <path>`：显式指定输出路径；不传时自动按检测到的关键词/短标题命名
- `--compare`：进入多论文对比模式（2 篇或多篇）
- `--items ...`：对比模式下输入文件路径列表（支持 pdf/html/txt）
- `--compare-style colorful|minimal`：对比页风格（默认 `colorful`）

读后感整理模式示例：

```powershell
python "<SKILL_ROOT>\scripts\paper_to_onepage_html.py" --reflection "<INPUT_DIR>\AMP_reflection.MD"
```

如果不传 `--out`，默认输出到同目录下、与源文件同名的 `.html` 文件。

## 输出

默认保留 2 个主文件：

- 主输出 `*.html`：一页总结版
- 源 PDF 的本地副本：默认与主输出同目录，并尽量同名，例如 `AMP.html` 对应 `AMP.pdf`

如传 `--keep-fulltext-html`，还会额外保留：

- `*_fulltext.html`：PDF 全文 HTML 展示页（完整读取）

如传 `--no-keep-pdf`，则 `--url` / `--query` 模式下载的 PDF 会在生成后删除，不在输出目录保留。

在 `--compare` 模式下，默认生成彩色简约对比页；且相同点 / 异同点均使用表格（table）展示。

在 `--reflection` 模式下，默认生成双栏的一页反思页：

- 顶部：标题、导语、问题焦点
- 主体：按原文顺序保留段落、编号列表、图片
- 高亮：对带“为什么 / 待确认 / 查证 / ?”等语气的段落做提示样式

其中主输出目标是**一页内信息密集展示**：

- 顶部：标题、作者、来源、链接
- 中部：核心摘要、方法流程、关键术语解释
- 底部：指标表、局限性、给初学者的理解路径

## 约束说明

- 流程固定为：`获取 PDF（query/url/pdf）-> 完整读取 -> 全文 HTML（中间产物）-> 总结一页 HTML`
- “完整详细读取”指读取所有可解析文本页；如果是扫描件图像 PDF，文本质量受 OCR 缺失影响

## 依赖

自动安装缺失依赖：

- `PyMuPDF`（必需，用于读取 PDF 文本）
- `requests`（可选；缺失或失败时自动降级到系统 `curl`）
- 系统 `curl`（Windows 10+ 自带；作为网络降级通道，对应 `/web-search-fallback`）
