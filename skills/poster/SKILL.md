---
name: poster
description: "HTML/CSS A4 海报生成。从沙龙/活动 Markdown 文件生成科技风 A4 海报 PDF/PNG。Use when user mentions: poster, 海报, 海报生成, make poster, generate poster, 活动海报, 沙龙海报."
---

# Poster Skill — HTML/CSS A4 海报生成

从沙龙/活动 Markdown 文件生成清爽科技风 A4 海报，支持 HTML / PDF / PNG 三种输出格式。

**技术栈**: Playwright + HTML/CSS + Jinja2 + pdf2image + qrcode（零 LaTeX 依赖）

## 输入格式

MD 文件需包含以下结构（参考 `references/template.MD`）：

```markdown
【活动标题】
日期：5.10（日）
时间：22：00-22：30
形式：每人3分钟分享+2分钟观众互动

分享人：
1. 姓名（班级）分享主题/进度描述
2. 姓名（班级）分享主题/进度描述
...

点击链接入会，或添加至会议列表：
https://meeting.tencent.com/dm/xxx

#腾讯会议：167-742-406

团队：开源社区部
愿景：打造高校圈子具身智能开源社区 Top 1
赛道：双赛道体系 — Awesome Repo 导向（新人入门）→ 立项 Contribute（进阶贡献）
招新：用一周时间入门具身智能，加入我们一起从零实践！
亮点：每位分享人仅用一周左右的学习与实践，即可上手汇报——加入我们，你也可以！

GitHub：Thu-FuRoc | https://github.com/Thu-FuRoc
飞书：开源社区部 | https://lcnxgbkker34.feishu.cn/wiki/xxx
HuggingFace：Thu-FuRoc | https://huggingface.co/Thu-FuRoc

logo：![alt text](sources/logo.jpg)
姓名1：![alt text](sources/photo1.jpg)
姓名2：![alt text](sources/photo2.jpg)
```

### 支持的字段

| 字段 | 格式 | 必填 | 说明 |
|------|------|------|------|
| 标题 | `【标题】` | 是 | 海报主标题 |
| 日期 | `日期：...` | 是 | 头部 meta 区 |
| 时间 | `时间：...` | 是 | 头部 meta 区 |
| 形式 | `形式：...` | 否 | 头部 meta 区（如"每人3分钟分享+2分钟互动"） |
| 分享人 | `1. 姓名（班级）主题` | 是 | 支持 2-4 人，括号内班级可选 |
| 会议链接 | URL 独占一行 | 否 | 头部 meta 区可点击跳转 + Footer QR 码 |
| 会议号 | `#腾讯会议：XXX` | 否 | 头部 meta 区 + 底部 footer |
| 团队 | `团队：...` | 否 | 底部团队介绍区块 |
| 愿景 | `愿景：...` | 否 | 团队区块内 |
| 赛道 | `赛道：...` | 否 | 团队区块内（标签样式） |
| 招新 | `招新：...` | 否 | 团队区块底部横幅 |
| 亮点 | `亮点：...` | 否 | 团队区块内，斜体高亮显示 |
| GitHub | `GitHub：显示名 \| URL` | 否 | QR 码 22mm + 标签，HTML 版 QR 可点击 |
| 飞书 | `飞书：显示名 \| URL` | 否 | QR 码 22mm + 标签，HTML 版 QR 可点击 |
| HuggingFace | `HuggingFace：显示名 \| URL` | 否 | QR 码 22mm + 标签，HTML 版 QR 可点击 |
| Logo | `logo：![...](path)` | 否 | 圆形头像 20mm，与社团名齐平 |
| 头像 | `姓名：![...](path)` | 否 | 圆形头像 18mm，模糊匹配姓名绑定 |

### 固定元素（无需 MD 字段）

- **社团名**: Logo 旁固定显示 "清华大学未来智能机器人兴趣团队 / Future Robotics Club, FuRoC"
- **部门行**: 固定显示 "开源社区部 Open Source Department"

### 链接格式说明

链接字段支持两种写法：

1. **带显示名**（推荐）：`GitHub：Thu-FuRoc | https://github.com/Thu-FuRoc` → QR 下方显示 "GitHub: Thu-FuRoc"
2. **仅 URL**：`GitHub：https://github.com/Thu-FuRoc` → 显示为 "GitHub"

## 工作流程

### Step 1: 获取输入文件

询问用户提供 MD 文件路径：

```
请提供要生成海报的 .MD 文件路径。
```

### Step 2: 读取并验证

1. 使用 Read 工具读取 MD 文件
2. 检查是否包含必要的结构信息（标题、日期、分享人）
3. 检查图片路径是否存在（`sources/` 目录）

### Step 3: (可选) 生成插画

如果海报需要 AI 插画来丰富视觉效果，可调用 `/ai-gen` 为每位分享人的主题生成插画。

### Step 4: 生成海报

使用 Bash 工具执行：

```bash
# 仅生成 HTML（可在浏览器预览，链接/QR 码可点击）
python "<LOCAL_USER>/.claude/skills/poster/poster_gen.py" "<MD文件路径>"

# 生成 HTML + PDF（强制单页 A4）
python "<LOCAL_USER>/.claude/skills/poster/poster_gen.py" "<MD文件路径>" --pdf

# 生成 HTML + PDF + PNG（PNG 由 PDF→300dpi 转换）
python "<LOCAL_USER>/.claude/skills/poster/poster_gen.py" "<MD文件路径>" --pdf --png

# 仅生成 PNG（自动先生成 PDF 再转 PNG）
python "<LOCAL_USER>/.claude/skills/poster/poster_gen.py" "<MD文件路径>" --png

# 带插画图片
python "<LOCAL_USER>/.claude/skills/poster/poster_gen.py" "<MD文件路径>" --pdf --png \
  --illustrations img1.png img2.png img3.png img4.png
```

脚本会：
- 解析 MD 文件提取结构化数据
- 为每个链接字段生成 QR 码（base64 data URI，嵌入 HTML）
- 用 Jinja2 模板渲染 HTML/CSS
- `--pdf`: 用 Playwright (Chromium) 将 HTML 转为单页 PDF
  - 设置 A4 viewport (794x1123)
  - 使用 screen media（确保 `overflow:hidden` 生效，不会分页）
  - **自动溢出检测**: 渲染后测量 content 实际高度 vs 可用空间，超出时打印 `[WARN]`
- `--png`: 用 pdf2image 将 PDF 转为 PNG（300dpi，与 PDF 完全一致）

### Step 5: (可选) 生成推广文案

使用 `--copy` 从 MD 数据生成精简推广文案（带 emoji），**自动复制到剪贴板**：

```bash
# 生成文案并复制到剪贴板（Windows UTF-8）
python "<SKILL_ROOT>/poster/poster_gen.py" "<INPUT_MD>" --copy 2>/dev/null > "$env:TEMP/poster_copy.txt" && powershell -Command "Get-Content -Path '$env:TEMP/poster_copy.txt' -Encoding UTF8 | Set-Clipboard"
```

**流程**: MD 解析 → LLM 语义精简（每条主题控制在 15 字以内） → 格式化文案 → UTF-8 管道 → PowerShell 写入剪贴板

- 调用当前 Claude Code 的同一个 LLM API（`ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`）
- LLM 负责语义精简，脚本负责格式化（标题 + 🚀分享阵容 + 精简内容 + ⏰📍🔗尾部）
- 如果 LLM 调用失败（网络/key 问题），自动回退为未精简的原始输出
- 执行后直接 Ctrl+V 粘贴即可

### Step 6: 检查结果

1. 检查 HTML/PDF/PNG 是否生成成功
2. 检查是否有 `[WARN] Content overflow` 警告
   - 如有溢出警告，需减小 header 高度或精简内容
3. 告知用户输出路径
4. 如果效果不理想，可直接编辑 HTML/CSS 模板调整样式

## 海报布局

```
┌─────────────────────────────────────────────────┐
│            开源社区部 Open Source Dept            │  Header
│ [Logo] 清华大学未来智能机器人兴趣团队              │  (80mm)
│        Future Robotics Club, FuRoC              │
│                                                  │
│               【活动标题】                        │
│                                                  │
│ ● 日期  ● 时间  ● 形式                          │
│ ● 会议号  ● 链接(可点击)                         │
├─────────────────────────────────────────────────┤
│              ── 分享人 ──                        │
│  ┌──────────┐  ┌──────────┐                     │
│  │ [头像]    │  │ [头像]    │                     │
│  │ 姓名 班级 │  │ 姓名 班级 │   Content           │
│  │ 主题描述  │  │ 主题描述  │   (~199mm可用)       │
│  └──────────┘  └──────────┘                     │
│  ┌──────────┐  ┌──────────┐                     │
│  │  ...      │  │  ...      │                     │
│  └──────────┘  └──────────┘                     │
│                                                  │
│  [插画1] [插画2] [插画3] [插画4]  (可选)         │
│                                                  │
│  ┌──────────────────────────────────┐            │
│  │ [开源社区部] 愿景描述             │  Team      │
│  │ [赛道1] Awesome  [赛道2] Contrib │  Section   │
│  │      招新横幅                     │            │
│  │  亮点: 斜体高亮文字               │            │
│  │ [QR:GitHub] [QR:飞书] [QR:HF]    │            │
│  └──────────────────────────────────┘            │
├─────────────────────────────────────────────────┤
│ 腾讯会议  167-742-406    meeting-url    [QR入会]  │  Footer
└─────────────────────────────────────────────────┘  (18mm)
```

**空间分配**: Header 80mm + Footer 18mm = 98mm 固定，Content 可用 ~199mm

## 设计规格

- **纸张**: A4 (210mm x 297mm)，强制单页
- **技术栈**: Playwright + Jinja2 + CSS Grid/Flexbox + pdf2image + qrcode
- **Header (80mm)**: 部门行 + 深蓝绿渐变背景 + Logo(圆形 20mm) + 社团名(中英文两行，固定) + 标题(28pt) + meta(日期/时间/形式/会议号/可点击链接)
- **Content (~199mm)**: 分享人卡片 2x2 网格（头像 18mm + 姓名 + 班级 + 主题），四色边框区分（teal/blue/violet/orange）
- **Illustrations**: (可选) 4 张 AI 生成主题插画，1x4 等宽网格
- **Team Section**: 团队徽章 + 愿景 + 双赛道标签 + 招新横幅 + 亮点(斜体) + QR 码 3 个(22mm，base64 嵌入)
- **Footer (18mm)**: 腾讯会议号 + 链接 + 入会 QR 码(12mm，base64 嵌入)
- **QR 码**: 所有链接字段自动生成 QR 码（qrcode 库），base64 PNG data URI 嵌入 HTML（无需外部文件，约 1KB/个）
- **单页保证**: `emulate_media("screen")` + A4 viewport + `overflow:hidden`，溢出时打印 `[WARN]` 提示实际尺寸
- **风格**: 清爽科技风，teal/blue 配色

## 输出格式

| 格式 | 标志 | 说明 | 工具 |
|------|------|------|------|
| HTML | (默认) | 可在浏览器预览，链接和 QR 码均可点击 | Jinja2 渲染 |
| PDF | `--pdf` | A4 单页，与打印一致 | Playwright (screen media) |
| PNG | `--png` | 300dpi A4 竖屏，由 PDF 转换 | pdf2image (poppler) |
| 文案 | `--copy` | LLM 语义精简推广文案（每条 15 字内），自动复制到剪贴板 | requests + ANTHROPIC_AUTH_TOKEN |

## 文件结构

```
<LOCAL_USER>/.claude/skills/poster/
├── skill.md              # 本文件
├── poster_gen.py          # 主脚本（MD 解析 + Jinja2 模板 + QR 生成 + PDF/PNG 转换 + 溢出检测）
└── references/
    └── template.MD        # MD 模板（新活动复制此文件填写）
```

## 依赖

```bash
pip install jinja2 playwright qrcode[pil] pdf2image
playwright install chromium
# pdf2image 还需安装 poppler（Windows: `choco install poppler` 或下载 poppler-bin）
```

## 错误处理

- 如果图片路径不存在：`[WARN]` 提示
- 如果内容超出单页：`[WARN] Content overflow: content Xmm > available Ymm`
- 如果 Playwright 未安装：`pip install playwright && playwright install chromium`
- 如果 pdf2image 未安装：`pip install pdf2image`（还需安装 poppler）
- 如果 qrcode 未安装：`pip install qrcode[pil]`
- 如果生成效果不理想，建议用户直接编辑 HTML 模板

## 直接使用

```
/poster D:\path\to\salon.MD
/poster 帮我生成一张沙龙海报
```
