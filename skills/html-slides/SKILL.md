---
name: html-slides
description: >-
  将 Markdown 源文件转为 16:9 HTML 演示文稿，再用浏览器导出 PDF。输出单个自包含 `.html` + `.pdf`，采用 Beamer 式简洁排版骨架。
---

# html-slides

将 **Markdown 源文件** 转为 16:9 HTML 演示文稿，再用浏览器导出 PDF。输出单个自包含 `.html` + `.pdf`，采用 **Beamer 式简洁排版骨架**（标题栏 + 细分隔线 + 圆角块 + 无页脚导航），保留清华紫配色。

流程固定为：**`.md` → `.html` → `.pdf`**。`.md` 是唯一源，不可省。

## When to Use

User mentions: `html-slides`, `html ppt`, `HTML 演示文稿`, `HTML 幻灯片`, `生成 PPT`, `生成幻灯片`, `md 转 ppt`, `markdown 幻灯片`, `slide`, `slides`, `演示文稿`, `presentation`, 或要把笔记/报告 `.md` 转成可视化幻灯片。

## Core Principles

1. **`.md` 是唯一源，不可省** — 必须先有一个 `.md`（用户提供路径或内容）。无 `.md` 则**要求用户提供，不要凭空生成**。重新运行即反映对 `.md` 的编辑。
2. **排版骨架 = Beamer 式简洁** — 每页由固定要素构成：**粗体紫标题栏（左对齐）+ 其下全宽紫色细分隔线 + 圆角浅紫块 + 无页脚无导航 + 大留白**。这是向 `latex-beamer` 靠拢的核心。
3. **读模板 + 填充生成，不从零手写 HTML** — 必须读取 `templates/default.template`，只替换 `{{TITLE}}` / `{{SLIDES}}` 两个占位符。
4. **配色保留清华紫** — 默认 `--accent #660874` / `--accent-strong #9B30FF`(分隔线) / `--block-bg #F9F5FC`。用户可改 accent（「蓝色」/ `#3366CC` 等）：**只改 `:root` 里几个 CSS 变量，骨架不动**。
5. **浅底强制** — 所有页用浅/白底（`#FEFEFF`、`#F9F5FC`），永不深色。
6. **16:9** — `.slide` 固定 `1280px × 720px`。
7. **字号下限 ≥ 20px** — 标题 28–36px，正文 20–24px，封面标题 56–68px。
8. **最多 10 页** — 内容密则多块分栏，不要塞爆。
9. **自包含 HTML** — CSS/JS 全内联，除 Noto Sans SC 字体 CDN 外无外部依赖。

## .md → 幻灯片 映射规则

对齐 `latex-beamer` 的标题层级语义（`#→section`、`##→frametitle`、`###→textbf`），落到 HTML：

| Markdown | 幻灯片 |
|---|---|
| 文档首个 `# 标题` | **封面页**：`cover-title` + 副标题（标题下首个段落）+ tags/团队 |
| `## 二级标题` | **一页**：`frametitle` = 该 `##` 文本，正文取到下一个 `##` 为止 |
| `### 三级标题` | 当前页内一个**圆角块**（`.block`），`.block-title` = 该 `###` 文本 |
| `---`（水平线） | **强制分页**（新 `.slide`） |
| `**粗体**` | `<strong>`（紫色强调） |
| `- 列表` / `1. 有序` | 块内 `<ul>` / `<ol>` |
| `| 表格 |` | `<table>` |
| `![alt](path)` | `<img>`（split 布局放 `.media`，否则入块） |
| `` `代码` `` / ```代码块``` | 块内 `<code>` / `<pre>` |
| `$…$` 行内公式 | 保留文本（PDF 由浏览器渲染，简单符号 OK；复杂公式建议截图） |

> 单个 `##` 章节内容过多（超 720px）→ 拆成多页（用 `---` 或自然断点），**不要缩到看不清**。

## Layout 原型（均用 Beamer 骨架元素构建）

- **Cover** — `.slide-cover`：浅紫渐变底 + 大标题 + 副标题 + tag 胶囊。
- **Standard** — `.titlebar > .frametitle` + `.divider` + 若干 `.block` / `.columns`。
- **Split**（图+文）— `.slide-split`：左 `.media`（460px 图，object-fit cover）+ 右标题栏+块。
- **Step/Grid** — `.grid` 4 列：每个 `.step .block` 顶部紫色条，用于时间线/路线图。
- **Conclusion** — Standard + 底部 `.conclude` 渐变紫横幅。

## Workflow（6 步：`..md` → `.html` → `.pdf`）

### Step 1：定位/要求 `.md`（必需）

1. 用户给了路径 → 读取该 `.md`。
2. 用户没给 → 扫描当前目录找 `.md`；找到多个则列出让其选；**一个都没有则要求用户提供，停在此步，不要继续**。
3. 顺便问 accent 色（默认清华紫）。

### Step 2：解析 `.md` → 幻灯片规划

套用上面的**映射规则**，产出页清单：

```
页1: 封面（标题 + 副标题 + 团队）
页2: ## 选题方向 —— Standard，2 个 block
页3: ## 技术框架 —— Split，左图右块
...
页N: 结论（conclude 横幅）
```

页数 > 10 → 提示合并/精简。**把清单给用户确认**再继续。

### Step 3：（可选）`/ai-gen` 出图

需要配图时调 `/ai-gen` 出封面图 / 章节插图（1536×1024 横图），存到 HTML 同级 `ai_gen_output/`。

### Step 4：读模板 + 填充 → 写 `.html`

1. **读取 `templates/default.template`**（本 skill 目录下）。
2. 按映射规则，把 `.md` 内容转成各 `<section class="slide …">…</section>`，拼成 `{{SLIDES}}`。
3. 封面页设 `.slide-cover` 且首张加 `is-active`；其余页默认隐藏，靠 JS 翻页。
4. 若用户改 accent → **仅改 `:root` 那几行 CSS 变量**，骨架与 JS 不动。
5. 输出**单个自包含 `.html`** 到 `.md` 同目录，文件名 = `.md` 名（如 `框架.md` → `框架.html`）。

骨架要点（务必遵守）：
- 每个非封面页：`<div class="titlebar"><div class="frametitle">标题</div></div><hr class="divider"><div class="body">…</div>`
- 块：`<div class="block"><div class="block-title">###标题</div>…</div>`
- 导航 JS 已在模板里，**不要再加可见导航条/页码**。

### Step 5：`.html` → `.pdf`（Playwright 逐页导出 + 合并）

**先做溢出自检**（借鉴 beamer 的 Overfull 闭环）：用 Playwright 量每个 `.slide` 的 `scrollHeight`，> 720px 即超框 → 缩字号/拆页/减块，修到不溢再导。

```python
from playwright.sync_api import sync_playwright
import fitz, os

def export_pdf(html_path, pdf_path):
    url = 'file:///' + os.path.abspath(html_path).replace('\\','/')
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1280,'height':720})
        page.goto(url)
        total = page.evaluate('window.slideCount')
        temps = []
        for i in range(total):
            page.evaluate(f'window.show({i})')
            page.wait_for_timeout(400)
            t = f'_s{i}.pdf'
            page.pdf(path=t, width='1280px', height='720px',
                     margin={'top':'0','bottom':'0','left':'0','right':'0'},
                     print_background=True)
            temps.append(t)
        browser.close()
    merged = fitz.open()
    for t in temps:
        d = fitz.open(t); merged.insert_pdf(d); d.close(); os.remove(t)
    merged.save(pdf_path); merged.close()
```

溢出自检片段（生成 .html 后跑）：
```python
with sync_playwright() as p:
    pg = p.chromium.launch().new_page(viewport={'width':1280,'height':720})
    pg.goto(url)
    for i in range(pg.evaluate('window.slideCount')):
        pg.evaluate(f'window.show({i})')
        h = pg.evaluate('document.querySelector(".slide.is-active").scrollHeight')
        if h > 720: print(f'OVERFLOW slide {i}: {h}px')  # 据此修复
```

### Step 6：交付

报告三路径 + 页清单：
- 源 `.md`（未改动）
- `.html`（浏览器打开可放映，空格/方向键翻页）
- `.pdf`（每页一张 16:9）

## Tips

- 要点 ≤ 2 行（20px 下）；每块 ≤ 4–5 条，避免溢出。
- 关键词用 `<strong>`（自动紫色），不要整段上色。
- 密集内容拆页，不要塞。
- split 布局图固定 460px 宽，`object-fit: cover`。
- `.md` 永远是唯一源：改 `.md` 重跑即可，不要手改 `.html`。

## Dependencies

- **Playwright** — `pip install playwright && playwright install chromium`（导 PDF）
- **PyMuPDF** — `pip install pymupdf`（合并 PDF）
- 字体：Noto Sans SC（Google Fonts CDN）
- `/ai-gen` — 可选出图
