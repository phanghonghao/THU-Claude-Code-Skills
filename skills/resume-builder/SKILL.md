---
name: resume-builder
description: 从用户上传的简历资料(PDF/Word/Markdown/已有 YAML/口述)生成排版好的单栏中文简历 PDF。默认 HTML→Chrome/Edge 无头打印（不依赖 LaTeX）；可选 --engine tex 走本机 xelatex（njq 风格 ctex 模板）。当用户提到「简历」「resume」「cv」「生成简历 PDF」「套用我的简历模板」时使用。
---

# resume-builder —— 数据驱动的中文简历生成器（HTML / LaTeX 双引擎）

把任意来源的简历资料，套用固定的单栏中文版式，输出为排版好的 **PDF**。
**默认引擎不依赖 LaTeX**：HTML 模板 + 系统 Chrome/Edge 无头打印（与 html2pdf 同机制）。
**可选 LaTeX 引擎**（`--engine tex`）：本机 xelatex 编译 njq 风格 ctex 模板，排印更精致。
两条路径都不使用任何 Overleaf token / cookie / API key，全程本机。

## 数据格式

固定结构，见 `schema/resume_schema.yaml`，可运行示例见 `examples/resume_data_example.yaml`。
板块：`personal / education / projects / lab_experience / clubs / competitions / skills / social_practice`。
每个经历板块都是**列表**，可写任意条数；字段留空或 `education[].optional: true` 自动不渲染。

## 工作流（务必按此执行）

### 1. 取输入并归一化成数据文件
根据用户给的资料，产出工作目录下的 `resume_data.yaml`（本机无 PyYAML 时改用 `resume_data.json`）：

- **已有 YAML/JSON**：直接用（字段对不上时按 schema 改写）。
- **PDF 简历**：先用 `pdf-reader`（或 `markitdown` / `pdf2word`+`word2md`）提取文本，再由你（Claude）读内容、按 schema 重组。
- **Word 简历**：用 `word2md` 或 `markitdown` 转 Markdown，再重组。
- **Markdown / TXT**：直接读，按 schema 重组。
- **纯口述**：根据用户描述组装成 schema。

重组时遵循：中文姓名进 `personal.name_cn`、英文姓名进 `name_en`；经历按时间倒序；无对应内容就留空，不要编造。

### 2. 一条命令出 HTML + PDF（开箱即用）
```bash
python "<SKILL_DIR>/scripts/build_resume.py" resume_data.yaml --out resume.html
```
> `<SKILL_DIR>` = 本 skill 目录。把脚本路径写全（含绝对路径）最稳。

**这一条命令会自动：** 生成 `resume.html`，再用系统 Chrome/Edge 无头打印**自动生成同名 `resume.pdf`**，并打印 PDF 路径与页数。
- 只想要 HTML：加 `--no-pdf`
- 指定 PDF 路径：加 `--pdf 路径.pdf`
- 纸张(A4)/边距由 HTML 模板的 `@page` CSS 控制
- 找不到浏览器时会优雅降级：只出 HTML 并提示用户在浏览器里手动打印

> `render_pdf.py` 仍可作为独立工具，用于「只有 HTML、想单独转 PDF」的场景。

### 2b. 可选：LaTeX 引擎（`--engine tex`）

想要更精致的排印（ctex 中文、`\titlerule` 分节线、njq 风格要点列表）时，改用 tex 引擎。**需要本机装好 xelatex**（MiKTeX 或 TeX Live，加入 PATH）。模板 `templates/classic_single.tex`（风格源自 njq 简历）。
```bash
python "<SKILL_DIR>/scripts/build_resume.py" resume_data.yaml --engine tex --out resume.tex
```
**这一条命令会自动：** 生成 `resume.tex` → 用 **xelatex 跑两遍**编译出同名 `resume.pdf` → 报页数 → **清理中间文件**（`.aux/.log/.out/.synctex.gz/.fls/...`，只留 `.tex` 与 `.pdf`）。
- 只想要 `.tex`：加 `--no-pdf`
- 数据里的 `% & _ # $ { } ~ ^ \` 等特殊字符由脚本自动转义，无需手动处理
- 证件照：复用同一条 `--photo / --photo-from / personal.photo` 管线，照片以 TikZ overlay 钉到页面右上角（编译两次已自动完成）
- **必须 xelatex**（ctex 中文）；脚本硬编码 xelatex，不可换 pdflatex
- **行距溢出**：模板默认 `\linespread{1.8}`（njq 为偏短内容撑满一页）。内容多、溢出第二页时，在 YAML 加一个 opt-in 旋钮调小：
  ```yaml
  tex:
    linespread: 1.3   # 1.0 紧凑 ~ 1.8 宽松
  ```
- MiKTeX 首次编译可能自动下载 `titlesec/enumitem/ctex` 等宏包（慢一次）；若关了自动安装，按 `.log` 提示 `mpm --install=<pkg>`

### 3. 修改循环
用户要调整内容 → 改 `resume_data.yaml` → 重跑上面那一条命令（html 或 tex）。
要调版式：HTML 引擎改 `templates/classic_single.html` 的 CSS；tex 引擎改 `templates/classic_single.tex`（如 `\linespread`、`\titleformat`、`geometry` 边距），均无需改脚本。

## 证件照（可选 · 纯算法识别）

支持从原履历中**自动识别证件照并嵌入到生成简历的右上角**——**不调用任何视觉 / agent API**，全程本地算法（OpenCV + PyMuPDF）。

**三步流程：**
1. **识别** — `scripts/extract_photo.py` 定位证件照：
   - 矢量 PDF：直接读取内嵌图片的放置 bbox（最精确）；
   - 图片 / 扫描件：OpenCV「非页面白前景 + 局部密度」分割（照片是密集色块，文字稀疏）；
   - 兜底：边缘密度。
2. **抠图** — 裁出照片区域 → `<stem>_photo.png`（与 HTML 同目录，供 `.tex` 复用）。
3. **嵌入** — HTML/PDF：照片以 base64 注入页眉 `<img class="r-photo">`，CSS 绝对定位右上角（25×33mm，1 寸比例），有照片时页眉自动右侧留白避让。

**用法：**
```bash
# 自动：从原履历 PDF 识别 + 抠图 + 嵌入
python "<SKILL_DIR>/scripts/build_resume.py" resume_data.yaml \
    --photo-from 原履历.pdf --out resume.html

# 或直接指定现成照片
python "<SKILL_DIR>/scripts/build_resume.py" resume_data.yaml --photo 证件照.png
```
也可在 YAML 写 `personal.photo: 证件照.png`。优先级：`--photo` > `--photo-from` > `personal.photo`。**不加任何照片参数时输出与原来完全一致**（特性 opt-in）。

> 单独提取：`python "<SKILL_DIR>/scripts/extract_photo.py" 原.pdf --out photo.png`

**关于 `.tex`**：`--engine tex` 会直接生成并编译 `.tex`（证件照用 TikZ overlay 钉到右上角，与上面 HTML 的 base64 注入是同一张 `<stem>_photo.png`）。无需手写 TikZ——见上文「2b. 可选：LaTeX 引擎」。

## 输出位置约定

`resume_data.yaml` / `resume.html` / `resume.pdf` 写到**调用时的当前工作目录**（或用户指定路径）。
**不要**往 skill 目录里写生成物——保持 skill 目录只读、可整体打包分享。

## 禁止事项

- **默认 HTML 引擎**不调用 pdflatex / xelatex / tlmgr / MiKTeX / Overleaf，也不写 `.tex`。
- **`--engine tex` 是显式 opt-in**：仅调用**本机** xelatex 编译，不联网、不用任何 Overleaf token / cookie / API key（包括用户历史 `tools/` 里的那些）。
- 不要为“修复中文”在默认路径上装 TeX——浏览器原生支持中文；只有用户主动选 tex 引擎时才依赖 xelatex（由本机已装的 MiKTeX/TeX Live 提供，不要为此联网下载新发行版）。

## 常见问题

- **找不到浏览器**（默认引擎）：提示用户安装 Chrome 或 Edge，或用 `--browser <路径>` 指定。
- **PyYAML 缺失**：把数据写成 `.json` 再跑（或 `pip install pyyaml`）。
- **想预览**：HTML 引擎生成 `resume.html` 后可直接在浏览器打开；tex 引擎看 `resume.pdf`。
- **tex 引擎找不到 xelatex**：装 MiKTeX 或 TeX Live 并加入 PATH；或退回默认 HTML 引擎（不带 `--engine`）。
- **tex 编译缺包**：MiKTeX 默认自动安装；失败时按 `.log` 提示 `mpm --install=<pkg>` 装 `titlesec/enumitem/ctex` 等。
- **tex 溢出到第二页**：在 YAML 调小 `tex.linespread`（如 `1.3`），或精简内容。
