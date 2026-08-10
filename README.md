# THU-Awesome-Skills

> A collection of 50 general-purpose [Claude Code](https://docs.anthropic.com/en/docs/claude-code) custom skills for academic workflows, project management, and developer productivity.
>
> 50 个通用型 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 自定义 Skill，覆盖学术工具、项目管理、开发效率等场景。

---

## For Codex Users / Codex 用户指南

![Best CLI Agent? Codex or Claude Code](assets/sync-diagram.png)

These skills are primarily designed for **Claude Code**, but they work seamlessly in **Codex** as well. To use them in Codex:

**If you are a Codex user**, simply install the skills into your Claude Code skills directory first, then use the built-in sync tools to copy them into Codex:

1. Install skills as described above (into `~/.claude/skills/` or `%USERPROFILE%\.claude\skills\`)
2. In Claude Code, run `/claude2codex` to sync all skills from Claude to Codex
3. Or sync a single skill: `/claude2codex <skill-name>`

This will copy all user skills from `%USERPROFILE%\.claude\skills` into `%USERPROFILE%\.codex\skills`, while preserving Codex's built-in `.system` skills.

**Reverse sync** (Codex → Claude): Use `/codex2claude` to sync skills from Codex back into Claude Code.

Both sync tools include:
- Automatic Claude environment discovery via `where claude`
- Junction/link resolution (copies real contents)
- SKILL.md case normalization (`skill.md` → `SKILL.md`)
- Post-sync verification before backup cleanup
- Full sync and single-skill sync modes

---

## Skills List / Skill 列表

| # | Skill | Description / 功能 | Command / 命令 | Dependencies / 依赖 |
|---|-------|-------------------|----------------|---------------------|
| 1 | [notes](skills/notes/) | Markdown note formatting, image renaming, dual-column layout | `/notes` | None |
| 2 | [cheatsheat](skills/cheatsheat/) | Markdown → A4 three-column cheatsheet PDF | `/cheatsheat` | None |
| 3 | [assignment](skills/assignment/) | University assignment management (read → MD → solve → PDF) | `/assignment` | MiKTeX/TeX Live, Python (optional) |
| 4 | [lab-report](skills/lab-report/) | Lab report rewriter v5.0 (PDF/DOCX → MD → PDF) | `/lab-report` | pdfplumber, python-docx, matplotlib |
| 5 | [latex-beamer](skills/latex-beamer/) | Markdown → LaTeX Beamer slides (CJKutf8 + ctex) | `/latex-beamer` | MiKTeX/TeX Live (xelatex) |
| 6 | [github-trending](skills/github-trending/) | Explore trending GitHub repos across AI/tech domains | `/github-trending` | curl (optional) |
| 7 | [git-push](skills/git-push/) | Quick git commit + push with confirmation flow | `/git-push` | git |
| 8 | [merge](skills/merge/) | Merge multiple videos into grid layout (2x2, 3x1, etc.) | `/merge` | `pip install av imageio imageio-ffmpeg Pillow numpy` |
| 9 | [project-managing](skills/project-managing/) | Project meeting notes & progress tracking | `/project-managing` | python-docx (optional) |
| 10 | [which-key](skills/which-key/) | Check which API key the current Claude Code session uses | `/which-key` | None |
| 11 | [ai-gen](skills/ai-gen/) | AI image & video generation via paratera API (multi-model) | `/ai-gen` | paratera API key |
| 12 | [html2tex](skills/html2tex/) | HTML to LaTeX converter | `/html2tex` | None |
| 13 | [img-reader](skills/img-reader/) | Local image analysis with 3-tier fallback (PIL → GLM-4V → OCR) | `/img-reader` | PyMuPDF, Pillow (optional) |
| 14 | [invoice-analyzer](skills/invoice-analyzer/) | Invoice recognition & financial status tracking | `/invoice-analyzer` | None |
| 15 | [md2docx](skills/md2docx/) | Markdown to Word (.docx) converter | `/md2docx` | python-docx |
| 16 | [md2tex](skills/md2tex/) | Markdown to LaTeX + PDF (XeLaTeX + ctex) | `/md2tex` | MiKTeX/TeX Live (xelatex) |
| 17 | [pdf-reader](skills/pdf-reader/) | PDF text extraction via PyMuPDF (fitz) | `/pdf-reader` | PyMuPDF |
| 18 | [plot-train-Z1](skills/plot-train-Z1/) | Z1 12DOF training learning curve plots & A4 PDF report | `/plot-train-Z1` | matplotlib, TensorBoard |
| 19 | [poster](skills/poster/) | HTML/CSS A4 poster generation from Markdown | `/poster` | None |
| 20 | [python-env](skills/python-env/) | Python version switching & virtual environment management | `/python-env` | None |
| 21 | [start_claude](skills/start_claude/) | Manage & launch Claude Code instances with different API keys | `/start_claude` | None |
| 22 | [codex2claude](skills/codex2claude/) | Sync Codex skills into Claude Code | `/codex2claude` | PowerShell |
| 23 | [claude2codex](skills/claude2codex/) | Sync Claude Code skills into Codex | `/claude2codex` | PowerShell |
| 24 | [word2html](skills/word2html/) | Word (.docx) to standalone HTML (tables, images, math) | `/word2html` | python-docx |
| 25 | [word2md](skills/word2md/) | Word (.docx) to Markdown with OMML → LaTeX math conversion | `/word2md` | python-docx, lxml |
| 26 | [any2md](skills/any2md/) | Universal document → Markdown converter (auto-routes DOCX/PPTX/XLSX/PDF) | `/any2md` | markitdown, PyMuPDF, python-docx |
| 27 | [assignment-word](skills/assignment-word/) | Edit & fill Word (.docx) — replace text, insert images, fill tables | `/assignment-word` | python-docx |
| 28 | [claude2anti](skills/claude2anti/) | Sync Claude Code skills into Antigravity (Gemini) | `/claude2anti` | None |
| 29 | [embodied-ai-agent](skills/embodied-ai-agent/) | Bilibili & GitHub embodied AI research → Chinese Wiki drafts | `/embodied-ai-agent` | OpenAI API (optional) |
| 30 | [html2pdf](skills/html2pdf/) | HTML → paginated PDF via Chrome/Edge headless | `/html2pdf` | Chrome or Edge |
| 31 | [html-slides](skills/html-slides/) | HTML slide-style presentation builder | `/html-slides` | None |
| 32 | [markitdown](skills/markitdown/) | Multi-format → Markdown via Microsoft markitdown (PDF/PPTX/XLSX/EPUB) | `/markitdown` | markitdown |
| 33 | [paper-html-onepage](skills/paper-html-onepage/) | arXiv paper → single-page A4 HTML summary | `/paper-html-onepage` | PyMuPDF |
| 34 | [pdf2word](skills/pdf2word/) | PDF → Word (.docx) preserving layout, tables, images | `/pdf2word` | PyMuPDF, python-docx |
| 35 | [reflection2xhs](skills/reflection2xhs/) | Reflection Markdown → Xiaohongshu-style A4 poster | `/reflection2xhs` | OpenAI API (optional) |
| 36 | [word2pdf](skills/word2pdf/) | Word (.doc/.docx) → PDF via Word COM or LibreOffice | `/word2pdf` | Microsoft Word or LibreOffice |
| 37 | [resume-builder](skills/resume-builder/) | Resume (PDF/Word/MD/YAML) → single-column CN resume PDF, **no LaTeX** | `/resume-builder` | Chrome or Edge |
| 38 | [paper-repro](skills/paper-repro/) | arXiv paper → understand + minimal reproduction + cost estimate | `/paper-repro` | PyMuPDF, git |
| 39 | [web-search-fallback](skills/web-search-fallback/) | Zero-MCP web search & URL reader (arXiv/GitHub/S2/curl) | `/web-search-fallback` | curl, gh (optional) |
| 40 | [jianying-editor](skills/jianying-editor/) | JianYing (剪映) AI auto-editing wrapper (record, subtitles, export) | `/jianying-editor` | JianYing, Python |
| 41 | [certificate](skills/certificate/) | Auto-generate e-certificate PNGs from salon posters | `/certificate` | None |
| 42 | [start_codex](skills/start_codex/) | Launch & manage Codex CLI instances with isolated API-key profiles | `/start_codex` | codex CLI |
| 43 | [sys-health](skills/sys-health/) | One-shot read-only health snapshot of this machine (CPU/RAM/disk/GPU) | `/sys-health` | WSL2 (optional) |
| 44 | [gpu-connect](skills/gpu-connect/) | SSH to a GPU server & report read-only status snapshot (GPU/disk/envs) | `/gpu-connect` | ssh |
| 45 | [gpu-train](skills/gpu-train/) | Monitor & manage remote RL training on the RTX PRO 6000 over SSH | `/gpu-train` | ssh, Slurm |
| 46 | [autodl-5090](skills/autodl-5090/) | Read-only monitor for RL training on the AutoDL RTX 5090 box (SSH) | `/autodl-5090` | ssh |
| 47 | [rtx-training-capture](skills/rtx-training-capture/) | Verify RTX training results, record best-iter video, pull artifacts | `/rtx-training-capture` | ssh |
| 48 | [unilab-train](skills/unilab-train/) | Monitor & manage UniLab RL training on local WSL (CPU-only) | `/unilab-train` | WSL2, UniLab |
| 49 | [unilab-rollout-trace](skills/unilab-rollout-trace/) | Record headless rollout trace from a UniLab policy → 4-panel stability figure | `/unilab-rollout-trace` | UniLab, matplotlib |
| 50 | [training-log-update](skills/training-log-update/) | Append/create the daily training-log entry in house style | `/training-log-update` | None |

---

## Installation / 安装

### Quick Install / 快速安装

```bash
# Clone the repo
git clone https://github.com/phanghonghao/THU-Awesome-Skills.git

# Copy all skills to your Claude Code skills directory
cp -r THU-Awesome-Skills/skills/* ~/.claude/skills/
```

### Install a Single Skill / 安装单个 Skill

```bash
# Example: install only the merge skill
mkdir -p ~/.claude/skills/merge
cp THU-Awesome-Skills/skills/merge/* ~/.claude/skills/merge/
```

### Windows

```powershell
# Copy all skills
Copy-Item -Recurse THU-Awesome-Skills\skills\* $env:USERPROFILE\.claude\skills\

# Or install a single skill
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills\merge"
Copy-Item THU-Awesome-Skills\skills\merge\* "$env:USERPROFILE\.claude\skills\merge\"
```

---

## Skill Details / 各 Skill 使用说明

### 1. notes — Markdown 笔记格式化

- Rename images based on content/heading context
- Auto-add heading markers (`# ## ###`)
- Optional dual-column layout for compact PDF
- Broken image reference recovery

### 2. cheatsheat — A4 三栏小抄

- Convert Markdown notes to compact A4 3-column layout
- Font size: 10.5px (小六), margins: 10mm
- Smart image sizing: large images 95%, small images 45% side-by-side
- Export to PDF via browser print

### 3. assignment — 大学作业管理

Full workflow: read assignment document → convert to Markdown → auto-solve → compile PDF.

| Command | Function |
|---------|----------|
| `/assignment [course] [hw#]` | Create assignment folder, read questions |
| `/assignment complete` | Auto-solve all questions |
| `/assignment done` | Compile MD → PDF |
| `/assignment auto` | One-click: solve + compile |
| `/assignment revise` | Check & fix LaTeX formatting |

Supports PDF, images (OCR), Word (.docx), Markdown input.

### 4. lab-report — 实验报告改写

Rewrite lab reports while preserving structure. Interactive workflow for personal info, images, data, and subjective answers.

| Command | Function |
|---------|----------|
| `/lab-report <course> <path>` | Read report → generate MD template |
| `/lab-report fill` | Fill personal info & subjective answers |
| `/lab-report chart` | Generate matplotlib charts from Excel |
| `/lab-report done` | MD → TEX → PDF |

### 5. latex-beamer — LaTeX Beamer 幻灯片

Convert Markdown to LaTeX Beamer presentations with incremental sync support.

- Dual version: CJKutf8 (pdflatex) + ctex (XeLaTeX)
- Incremental sync: detect .md changes and update .tex
- Smart image placement based on section keywords
- Auto-compile to PDF

### 6. github-trending — GitHub 热门项目探索

Browse trending repos across AI/tech domains with bilingual output.

| Flag | Domain |
|------|--------|
| `--robotics` | Robotics & Embodied AI |
| `--agents` | AI Agents & Frameworks |
| `--mcp` | Model Context Protocol |
| `--llm` | LLM Tools & Inference |
| `--cv` | Computer Vision |
| `--3d` | 3D Reconstruction & Gaussian |
| `--driving` | Autonomous Driving |
| `--rl` | Reinforcement Learning |
| `--audio` | TTS & Audio AI |
| `--vla` | Vision-Language-Action Models |

### 7. git-push — 快速 Git 推送

Interactive git commit + push workflow:
1. Ask for commit description
2. Show changes for confirmation
3. Add → commit → push

### 8. merge — 视频网格拼接

Merge multiple MP4 videos into grid layouts (2x1, 3x1, 2x2, 3x2, custom NxM) with optional labels.

```bash
python <SKILL_ROOT>/merge_videos.py v1.mp4 v2.mp4 v3.mp4 v4.mp4 -t 2x2 --labels "A" "B" "C" "D"
```

### 9. project-managing — 项目会议记录

Generate and manage project meeting notes with progress tracking tables. Supports .docx import.

### 10. which-key — API Key 查询

Quickly check which API key profile the current Claude Code session is using. Read-only, no Bash required.

### 11. ai-gen — AI 生图/生视频

AI image & video generation via paratera API. Supports multiple model presets (豆包/GLM/MiniMax) with cross-series fallback.

- Text-to-image and text-to-video generation
- Multi-model combination for best coverage
- Batch generation from Markdown files

### 12. html2tex — HTML 转 LaTeX

Convert HTML content to LaTeX format.

### 13. img-reader — 本地图片读取分析

Local image analysis with 3-tier automatic fallback:
1. Read + PIL enhancement
2. GLM-4V-Flash (free API)
3. PaddleOCR (offline)

Zero MCP credit required.

### 14. invoice-analyzer — 发票识别分析

Analyze invoices in financial management directory and extract key information. Update financial list with invoice status.

### 15. md2docx — Markdown 转 Word

Convert Markdown files to Word (.docx) format with proper formatting preservation.

### 16. md2tex — Markdown 转 LaTeX + PDF

Convert .md to .tex (XeLaTeX + ctex) and compile to .pdf. Supports Chinese, tables, images, math formulas, code blocks.

### 17. pdf-reader — PDF 读取

Read and extract text from PDF files using PyMuPDF (fitz). Preferred over native Read tool for PDF files.

### 18. plot-train-Z1 — Z1 训练曲线绘图

Generate and sync Z1 12DOF training learning curve plots from TensorBoard data, compile a single-page A4 PDF report with plots + data analysis.

### 19. poster — A4 海报生成

HTML/CSS A4 poster generation from Markdown event files. Tech-style design, supports PDF/PNG output.

### 20. python-env — Python 环境管理

Python version switching and virtual environment management. Quick create/activate .venv with specified Python version.

### 21. start_claude — Claude Code 实例管理

Manage and launch Claude Code instances with different API keys. Supports session recovery and in-place key switching with `--continue`.

### 22. codex2claude — 同步 Codex → Claude

Synchronize Codex user skills into Claude Code skills directory. Supports full sync and single-skill sync. Auto-discovers Claude environment via `where claude`. Includes post-sync verification (target existence, SKILL.md presence, file count parity) with automatic backup cleanup.

### 23. claude2codex — 同步 Claude → Codex

Synchronize Claude Code user skills into Codex skills directory. Preserves Codex built-in `.system` skills. Supports full sync and single-skill sync. Includes post-sync verification with automatic backup cleanup.

### 24. word2html — Word 转 HTML

Convert Word (.docx) files to standalone HTML with tables, images, and math formulas. Handles merged cells, embedded images, and OMML math via MathJax.

### 25. word2md — Word 转 Markdown

Convert Word (.docx) files with Office Math formulas to clean Markdown with LaTeX. Handles OMML to LaTeX conversion, Greek letters, subscripts, superscripts, fractions.

### 26. any2md — 通用文档转 Markdown

Universal document-to-Markdown converter with automatic format routing. Auto-detects DOCX math and routes to word2md; uses markitdown for PPTX/XLSX/HTML/EPUB; supports PyMuPDF for high-fidelity PDF.

### 27. assignment-word — Word 文档填写

Edit and fill Word (.docx) documents programmatically — inspect structure, replace text, batch fill placeholders, insert images, and fill tables.

### 28. claude2anti — 同步 Claude → Antigravity

Synchronize Claude Code user skills into Antigravity (Gemini). Supports full sync and single-skill sync.

### 29. embodied-ai-agent — 具身智能调研 Agent

Research and organize Bilibili & GitHub embodied AI content. Generates Chinese Wiki drafts by topic, with optional Feishu push. Covers VLA, World Models, GR00T, ALOHA and more.

### 30. html2pdf — HTML 转 PDF

Convert HTML, especially slide-style presentations, into paginated PDF using Chrome or Edge headless printing.

### 31. html-slides — HTML 幻灯片

Build HTML-based slide presentations with rich formatting support.

### 32. markitdown — 多格式转 Markdown

Convert various document formats (PDF, DOCX, PPTX, XLSX, HTML, EPUB, images, IPYNB, ZIP) to Markdown using Microsoft's markitdown library.

### 33. paper-html-onepage — 论文单页总结

Automatically retrieve paper PDFs from arXiv by keyword, extract full text, and generate a single-page A4-style HTML summary.

### 34. pdf2word — PDF 转 Word

Convert PDF files to Word (.docx) while preserving layout, tables, images, and formatting.

### 35. reflection2xhs — 读后感转小红书海报

Convert reflection Markdown files into polished single-page Xiaohongshu-style A4 poster.

### 36. word2pdf — Word 转 PDF

Convert Word (.doc/.docx) to PDF. Auto-detects binary .doc vs .docx, then converts using Microsoft Word COM or LibreOffice headless.

### 37. resume-builder — 无 LaTeX 简历生成器

Turn any resume source (PDF / Word / Markdown / filled YAML / dictated) into a polished single-column Chinese resume PDF. **No LaTeX / MiKTeX / Overleaf** — renders an HTML template with the system Chrome/Edge headless `--print-to-pdf`.

- Faithful port of a fixed single-column CN layout (education / projects / lab / clubs / skills …)
- Variable-length sections, HTML-escaping, optional entries auto-skipped
- Inspired by [Resume-Matcher](https://github.com/srbhr/Resume-Matcher)'s HTML → headless-browser → PDF approach

### 38. paper-repro — 论文读懂 + 最小复现

One-stop "understand + minimal reproduction" for papers. Input an arXiv URL/ID/keyword/local PDF → single-page HTML summary (via `/paper-html-onepage`) → find code, analyze full-repro requirements, plan a minimal repro, run a minimal-scale experiment, and estimate full reproduction cost.

### 39. web-search-fallback — 零 MCP 联网搜索

Local zero-MCP web search & URL reader. Automatic fallback when MCP `web_search`/`webReader` hit rate limits (429/quota), or proactively for academic/GitHub queries. Routes to arXiv API, GitHub API (gh/curl), Semantic Scholar API, and direct curl fetch.

### 40. jianying-editor — 剪映自动化剪辑

High-level wrapper (JyWrapper) around JianYing (剪映) for AI-assisted auto-editing — screen recording, asset import, subtitle generation, web motion synthesis, and project export.

### 41. certificate — 电子证书生成

Automatically generate electronic-certificate PNGs from salon/seminar posters (e.g. 名人堂证书).

### 42. start_codex — Codex 实例管理

Manage and launch Codex (codex CLI) instances with different API keys / profiles. Supports launch (isolated `CODEX_HOME`, new session), `--continue` (resume last session inside an isolated profile), and `--check` (test each key's availability). The root `~/.codex` is never touched.

### 43. sys-health — 本机系统体检

One-shot read-only health snapshot for this machine (AMD Ryzen 7 laptop, CPU-only RL in WSL2): CPU load, memory, swap, disk usage, SSD write activity from checkpoints, active training-process detection, and Windows host (CPU/disk/GPU).

### 44. gpu-connect — GPU 服务器连接

Connect to a GPU server over SSH and report a one-shot read-only status snapshot — connectivity, identity, GPU util/mem/temp, disk, RAM, CPU load, conda envs. Default target A100 (`ssh a100`); pass any configured alias (`autodl`, `spark`, `dreamzero`) or a raw remote command.

### 45. gpu-train — 远程训练管理 (RTX PRO 6000)

Monitor and manage remote RL training on the RTX PRO 6000 server over SSH — training status, tail logs, GPU usage, idle GPUs, my CUDA usage, Slurm jobs, failure analysis, simulation videos, multi-phase automation pipelines.

### 46. autodl-5090 — AutoDL 5090 训练监控

Lightweight, read-only monitor for RL training on the AutoDL RTX 5090 box over SSH. `--tail` follows live training logs and snapshots iteration/speed/ETA/metrics; `--status` gives a one-shot CPU/RAM/disk/GPU snapshot. Canonical call: `/autodl-5090 --tail --status`.

### 47. rtx-training-capture — RTX 训练成果归档

Check the latest training log, verify RTX training results, analyze success/failure, record the best-iteration video, and pull artifacts back to local.

### 48. unilab-train — UniLab 本地训练管理

Monitor and manage UniLab RL training on local WSL (CPU-only, no CUDA) — training status, tail logs with key metrics, best checkpoint, viser/TensorBoard viewers, resume interrupted runs, record Motrix demos.

### 49. unilab-rollout-trace — UniLab Rollout 稳定性图

Record a headless numeric rollout trace from a UniLab off-policy policy (SAC/FlashSAC) on MuJoCo, then plot a 4-panel stability figure (base height/fall, velocity tracking, effort, reward) with a one-line verdict. Works for any task.

### 50. training-log-update — 训练日志更新

Append or create the daily training-log entry (one `YYYY-MM-DD.md` per day) in the established house style — a one-line Headline plus explicit Done / Issues-and-fixes / Pending / Key-paths sections, with no media copied in (references real paths).

---

## Requirements / 系统要求

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (installed and configured)
- Python 3.x (for skills with Python scripts)
- MiKTeX / TeX Live (for assignment, lab-report, latex-beamer)

---

## License

[MIT](LICENSE)

---

## Acknowledgements / 致谢

- [jianying-editor-skill](https://github.com/luoluoluo22/jianying-editor-skill) — inspiration for the skill format (not included in this repo)

---

# THU Awesome Skills

A curated collection of reusable Codex skills, organized by publicability and
privacy risk.

## Public collection

This repository currently contains **33 skills**:

- **Document and format conversion**: `any2md`, `html2md`, `html2pdf`,
  `html2tex`, `markitdown`, `md2docx`, `md2tex`, `pdf-reader`, `pdf2word`,
  `word2html`, `word2md`, `word2pdf`
- **Research and knowledge workflows**: `github-trending`,
  `paper-html-onepage`, `paper-repro`, `repo-docs`, `repo-docs-zh`,
  `web-search-fallback`
- **Writing, presentation, and media utilities**: `cheatsheat`, `fincomp-deck`,
  `html-slides`, `latex-beamer`, `merge`, `notes`, `poster`
- **Skill and tool synchronization**: `claude2anti`, `claude2codex`,
  `codex2claude`, `git-push`
- **Specialized reusable tools**: `ai-gen`, `assignment-word`, `img-reader`,
  `resume-builder`

Install all public skills into a Codex or Claude skills directory by copying
the contents of `skills/`.

```powershell
Copy-Item -Recurse .\skills\* "$env:USERPROFILE\.codex\skills\"
```

## Classification policy

The source inventory was classified into three groups:

1. **Public**: reusable skills without a necessary dependency on personal
   servers, accounts, private projects, or personal records.
2. **Audit-only**: potentially reusable skills that require sanitization,
   permission checks, or removal of personal examples. From this group,
   `resume-builder` is the only skill included in this repository.
3. **Private or excluded**: skills tied to personal infrastructure, training
   jobs, credentials, local machine state, or external projects.

## Excluded source material

The following source groups are intentionally absent:

- All `ts-*` skills: retained with their original source owner and not part of
  this collection.
- All `lark-*` skills: retained with their original source owner and not part
  of this collection.
- `jianying-editor`: retained with its original source owner and not included.
- `oh-my-rss`: retained with its original source owner and not included.
- GPU, remote-training, API-key, machine-health, and personal logging skills.
- The remaining audit-only skills, including personal documents, financial
  workflows, certificates, and project-specific agents.
- Codex `.system` skills, credentials, logs, caches, `.env` files, and runtime
  artifacts.

## Provenance

The public skills were selected from the original local Codex skills inventory.
Excluded skills remain traceable to that original inventory but are not
redistributed here. Individual skills may retain their own upstream attribution
and license notices where applicable.

## License

MIT. See [LICENSE](LICENSE).
