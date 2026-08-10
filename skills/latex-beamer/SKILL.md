---
name: latex-beamer
description: >-
  LaTeX Beamer 幻灯片制作 - 将 Markdown 转换为 Beamer 演示文稿。
  支持 ctex 中文、数学公式、图片、表格。适用于答辩、汇报、演讲。
---

# LaTeX Beamer 智能同步 Skill

将 Markdown 笔记转换为 LaTeX Beamer 演示文稿，支持增量更新。

## Overview

**核心功能**：
1. **不存在则生成** - 如果 .tex 文件不存在，从 .md 完整生成
2. **存在则同步** - 如果 .tex 已存在，先检测 .md 变化，然后增量更新
3. **双向同步** - 支持 .md 和 .tex 内容的智能对比和同步
4. **单版本输出** - 统一使用 ctex (XeLaTeX) 编译，兼容中英文
5. **PPTX 输出** - `--pptx` 跳过 PDF 编译，直接从 .tex 生成 PPTX

## 命令行标志

| 标志 | 说明 | 行为 |
|------|------|------|
| *(无标志)* | 默认流程 | Step 1→2/3→4 (PDF 编译) → 5 (可选 PPTX) |
| `--pptx` | 仅生成 PPTX | 跳过 Step 4 (PDF 编译)，直接走 Step 5 (读取 .tex → 生成 gen_pptx.py → 执行) |
| `--pptx <path>` | 指定路径 + 仅 PPTX | 定位到 `<path>` 目录，跳过 PDF 编译，直接生成 PPTX |

### `--pptx` 的使用场景

1. **已有 .tex 和 .pdf，只需要 PPTX** — 不需要重新编译 PDF，直接从 .tex 生成 PPTX
2. **快速迭代 PPTX 排版** — 修改 gen_pptx.py 后重新执行，不用等 xelatex 编译
3. **没有 MiKTeX 环境** — 不需要 xelatex，只要有 .tex 文件就能生成 PPTX

## Workflow

### Step 1: 文件状态检测

检查目标 LaTeX 文件是否存在：

```bash
# 检查文件是否存在
ls docs/presentation/templates/latex/xxx/main.tex
```

**判断逻辑**：
- 如果不存在 → 走 **Step 2: 完整生成流程**
- 如果存在 → 走 **Step 3: 增量同步流程**

**`--pptx` 跳转逻辑**：
- 如果用户传入 `--pptx` 且 .tex 已存在 → **跳过 Step 2/3/4，直接走 Step 5**
- 如果用户传入 `--pptx` 但 .tex 不存在 → **先走 Step 2 生成 .tex，然后跳过 Step 4，走 Step 5**
- 如果用户传入 `--pptx` 指向 .tex 文件路径 → **直接读取该 .tex，走 Step 5**

---

## Step 2: 完整生成流程（文件不存在时）

### 2.1 分析 Markdown 文件

读取并分析 .md 文件结构：

```python
# 关键信息提取
- 项目名称: 从标题或 # 中提取
- 作者信息: 从 "团队成员" 或类似章节提取
- 章节结构: ## 标记的章节
- 图片引用: ![alt](path) 或 <img> 标签
- 表格数据: Markdown 表格格式
- 数学公式: $...$ 或 $$...$$
```

### 2.2 选择文档类型

根据用户需求选择：
- **Beamer 演示文稿**: `\documentclass{beamer}`
- **Article 文档**: `\documentclass{article}`

### 2.3 生成 .tex 文件（XeLaTeX + ctex）

```latex
\documentclass[aspectratio=169, 10pt]{beamer}
\usepackage[UTF8]{ctex}
% ... 其他设置
\begin{document}
% 内容（无需 CJK* 环境，原生支持中英文）
\end{document}
```

### 2.4 处理图片

1. 复制图片到 `sources/` 目录
2. 重命名为英文（中文转拼音）
3. 更新 LaTeX 中的引用路径

### 2.5 处理 GIF / 视频动画

当 .md 中引用了 `.gif`、`.mp4`、`.avi` 等动态媒体文件时，自动提取帧并嵌入为 PDF 动画。

#### 检测规则

扫描 .md 中的媒体引用（与图片相同语法）：
```markdown
![描述](path/to/demo.gif)
![描述](path/to/clip.mp4)
```

也扫描 `sources/` 目录中的 `.gif` 文件。

#### 帧提取流程

**GIF 提取**（使用 Pillow）：
```python
from PIL import Image
import os

def extract_gif_frames(gif_path, output_dir, max_width=200):
    """提取 GIF 帧到 output_dir/frame_0.png, frame_1.png, ..."""
    os.makedirs(output_dir, exist_ok=True)
    img = Image.open(gif_path)
    i = 0
    while True:
        frame = img.convert('RGB')
        w, h = frame.size
        new_w = min(max_width, w)
        new_h = int(h * new_w / w)
        frame = frame.resize((new_w, new_h), Image.LANCZOS)
        # 关键：文件名不使用前导零！animategraphics 需要 frame_0, frame_1, ...
        frame.save(os.path.join(output_dir, f'frame_{i}.png'))
        i += 1
        try:
            img.seek(i)
        except EOFError:
            break
    return i  # 返回总帧数
```

**视频提取**（使用 ffmpeg）：
```bash
# 从视频中每 N 帧提取一张 PNG（控制总帧数 <= 120）
ffmpeg -i input.mp4 -vf "fps=10,scale=200:-1" sources/video_name/frame_%d.png
```

#### 帧数控制

| 总帧数 | 处理策略 |
|--------|---------|
| ≤ 120 | 全部保留 |
| 120-300 | 每 2 帧取 1 帧 |
| > 300 | 每 N 帧取 1 帧，目标 ≤ 120 帧 |

帧率映射：
- GIF 原始 `duration` → `animategraphics` 帧率 = `1000 / duration_ms`
- 视频默认 10 fps

#### 目录结构

```
sources/
├── image1.png              # 静态图片
├── demo.gif                # 原始 GIF（保留）
├── demo/                   # 帧目录（与 GIF 同名）
│   ├── frame_0.png
│   ├── frame_1.png
│   └── ...
├── clip.mp4                # 原始视频
└── clip/                   # 帧目录
    ├── frame_0.png
    └── ...
```

#### LaTeX 集成

1. **在 preamble 添加**：
```latex
\usepackage{animate}
```

2. **在对应 frame 中使用 `\animategraphics`**：
```latex
% 语法: \animategraphics[选项]{帧率}{文件基础路径}{起始帧}{结束帧}
\animategraphics[autoplay,loop,width=0.5\textwidth]{10}{sources/demo/frame_}{0}{66}
```

3. **注意事项**：
   - 文件名必须是 `frame_0.png, frame_1.png, ...`（**无前导零**）
   - `\animategraphics` 会自动搜索 `frame_0.png`, `frame_0.pdf` 等格式
   - `autoplay` = 打开 PDF 自动播放；`loop` = 循环
   - **仅 Adobe Acrobat Reader 支持播放**，其他阅读器显示静态首帧
   - 每个 GIF/视频的帧数较多会显著增大 PDF 体积（控制帧数 ≤ 120）

### 2.5 生成 README.md

说明两个版本的区别和使用方法。

---

## Step 3: 增量同步流程（文件存在时）

### 3.1 对比 .md 文件变化

读取最新的 .md 文件，对比关键内容：

```python
# 检测变化的内容类型
1. 新增图片: 新的 ![alt](path) 或 <img> 标签
2. 新增 GIF/视频: ![alt](path) 中 path 以 .gif/.mp4/.avi 结尾
3. 新增章节: 新的 ## 标题
4. 数据更新: 数字、名称等信息变化
5. 结构调整: 章节顺序、层级变化
```

**GIF/视频处理**（检测到新动态媒体时）：
1. 检测文件扩展名：`.gif`, `.mp4`, `.avi`, `.mov`, `.webm`
2. 执行帧提取流程（参见 Step 2.5）
3. 在 .tex 中使用 `\animategraphics` 嵌入动画
4. 确保 `\usepackage{animate}` 在 preamble 中（仅首次添加）

### 3.2 先更新 .md 文件

**如果 .md 文件在 docs/documentation/ 目录中**：

1. **定位对应的 .md 文件**：
   - 例：`main.tex` → `项目分享答辩框架.md`
   - 例：`team.tex` → `团队介绍.md`
   - 例：`presentation.tex` → `项目介绍.md`

2. **对比 .tex 和 .md 的内容差异**

3. **将 .tex 的变化反向同步到 .md**：

   #### A. 新增图片同步到 .md（智能定位）

   **分析图片内容，定位到对应章节**：

   1. **提取图片描述关键词**：
      - `solidworks_structure.png` → 关键词: "SolidWorks"、"硬件"、"结构"
      - `prototype_hardware.png` → 关键词: "原型"、"硬件"
      - `isbn_recognition.jpg` → 关键词: "ISBN"、"识别"
      - `ai_smart_cabinet.png` → 关键词: "智能柜"、"AI"

   2. **匹配章节规则**：

      | 图片关键词 | 匹配章节 | 插入位置 |
      |------------|----------|----------|
      | SolidWorks、硬件结构 | ### 2.2 硬件终端原型 | 该章节内 |
      | 原型、开发 | ### 2.2 硬件终端原型 | 该章节内 |
      | ISBN、识别 | ### 2.3 软件闭环功能 | 该章节内 |
      | 智能柜、AI | ### 2.1 产品定位 | 该章节内 |
      | 小程序、界面 | ### 2.3 软件闭环功能 | 该章节内 |
      | 商业、盈利 | ### 3.1 盈利模型 | 该章节内 |
      | SWOT、优势 | ### 3.2 SWOT分析 | 该章节内 |

   3. **插入到对应章节**：

      ```markdown
      ## 二、项目内容（原型与技术指标）(2.5 min)

      ### 2.2 硬件终端原型

      | 组件 | 规格参数 |
      |------|----------|
      | **机身规格** | 碳钢板结构 + 透明屏蔽玻璃，单柜 40-60 个独立格口（270×200×90mm/格） |
      | **控制核心** | 树莓派（Raspberry Pi）操作系统 |
      ...

      **🆕 新增图片**：
      - SolidWorks 硬件结构设计：
        ![SolidWorks 设计图](b8f5b5fba769e1ae4ddad46b23847fc7.png)
      - 开发原型配套图：
        ![原型硬件](image.png)
      ```

   4. **多张相关图片合并插入**：

      如果图片属于同一主题，使用组合插入：

      ```markdown
      ### 2.3 软件闭环功能

      ... 原有内容 ...

      **🆕 ISBN 识别功能测试**：
      ![识别成功案例](226a10bce9c554ec6ffd5f5b99c44834.jpg)
      ![ISBN 样例](image-1.png)
      ```

   5. **图片插入格式规范**：

      ```markdown
      **[图片类别]**：
      ![图片描述](图片路径)
      ```

   #### B. 添加更新日志

   在 .md 文件末尾添加更新记录：

   ```markdown
   ---
   ## 更新日志

   ### 2025-04-16
   - 新增 SolidWorks 硬件结构设计图
   - 新增开发原型配套图
   - 新增 ISBN 识别功能测试截图
   - 更新团队信息
   ```

   #### C. 同步规则优先级

   | 优先级 | 内容类型 | 同步要求 | 示例 |
   |--------|----------|----------|------|
   | **必须** | 人名信息 | .tex → .md | "洪誌慧" |
   | **必须** | 项目名称 | .tex → .md | "清园书享" |
   | **必须** | 新增图片 | .tex → .md | 新增图片引用 |
   | **应该** | 核心数据 | .tex ↔ .md | "4000万" |
   | **应该** | 章节标题 | .tex ↔ .md | 章节名称 |
   | **可选** | 具体描述 | 不强制同步 | 解释性文字 |

### 3.3 再更新 .tex 文件

**只更新变化的部分**：

#### A. 新增图片（智能定位插入）

1. **检测 .md 中新增的图片**

2. **分析图片归属章节**：

   ```python
   # 章节映射规则
   CHAPTER_MAP = {
       "solidworks|硬件结构|建模": "硬件终端原型",
       "原型|开发|配套": "硬件终端原型",
       "isbn|识别|扫描": "软件闭环功能",
       "智能柜|示意图": "产品定位",
       "小程序|界面|截图": "软件闭环功能",
       "盈利|收入|商业模式": "盈利模型",
       "swot|优势|劣势": "SWOT分析",
   }
   ```

3. **定位插入位置**：

   在 .tex 文件中找到对应章节的 `\section` 或 `\frametitle`，在其后插入：

   ```latex
   % ============================================================
   % 在 "硬件终端原型" 章节中
   % ============================================================

   \begin{frame}{硬件终端原型}
       % 原有内容...
   \end{frame}

   % 🆕 在该章节末尾插入新图片页面
   \begin{frame}{SolidWorks 硬件结构设计}
       \centering
       \includegraphics[width=\imgwidth]{solidworks_structure.png}
       \vspace{0.3cm}
       \small 智能书柜硬件结构建模（SolidWorks 设计）
   \end{frame}

   \begin{frame}{开发原型与硬件集成}
       \centering
       \includegraphics[width=\imgwidth]{prototype_hardware.png}
       \vspace{0.3cm}
       \small 开发原型配套图 - 硬件模块集成示意图
   \end{frame}
   ```

4. **相关图片合并插入**：

   如果多张图片属于同一主题，创建一个对比页面：

   ```latex
   % 🆕 ISBN 识别功能测试（双图对比）
   \begin{frame}{ISBN 识别功能测试}
       \centering
       \begin{columns}[T]
           \begin{column}{0.48\textwidth}
           \centering
           \includegraphics[width=0.95\textwidth]{isbn_recognition.jpg}
           \vspace{0.2cm}
           \small ISBN 识别成功案例
           \end{column}

           \begin{column}{0.48\textwidth}
           \centering
           \includegraphics[width=0.95\textwidth]{isbn_sample.png}
           \vspace{0.2cm}
           \small ISBN 条码样例
           \end{column}
       \end{columns}

       \vspace{0.5cm}

       \begin{block}{}
           \centering
           \small 基于视觉识别的自动 ISBN 扫描功能
       \end{block}
   \end{frame}
   ```

5. **插入位置优先级**：

   | 优先级 | 位置 | 条件 |
   |--------|------|------|
   | 1 | 对应章节内 | 能匹配到章节关键词 |
   | 2 | 章节结束后 | 该章节有明显结束标记 |
   | 3 | 下一章节前 | 无法匹配时，放在相关章节前 |
   | 4 | 文档末尾 | 兜底位置 |

#### B. 智能定位完整示例

**场景**：用户在 .md 文件开头添加了 4 张新图片

**Step 1: 分析图片**

```python
images = [
    "solidworks_structure.png",  # 描述: "solidworks的硬件结构图"
    "prototype_hardware.png",    # 描述: "开发原型配套图"
    "isbn_recognition.jpg",      # 描述: "测试ISBN识别成功案例"
    "isbn_sample.png",           # 描述: "ISBN样例"
]
```

**Step 2: 匹配章节**

```python
# 关键词匹配
solidworks_structure.png → ["solidworks", "硬件", "结构"] → 匹配: "硬件终端原型"
prototype_hardware.png → ["原型", "硬件"] → 匹配: "硬件终端原型"
isbn_recognition.jpg → ["isbn", "识别"] → 匹配: "软件闭环功能"
isbn_sample.png → ["isbn"] → 匹配: "软件闭环功能"
```

**Step 3: 插入位置定位**

在 .tex 文件中搜索：

```latex
% 搜索: \section{产品制作与改进方案}
% 找到该章节后，继续搜索子章节

% 搜索: \frametitle{硬件终端原型}
% 找到该 frame 后，在其后插入新图片页面

\begin{frame}{硬件终端原型}
    % 原有内容...
\end{frame}

% 🆕 在此位置插入 SolidWorks 相关图片
\begin{frame}{SolidWorks 硬件结构设计}
    \centering
    \includegraphics[width=\imgwidth]{solidworks_structure.png}
    \vspace{0.3cm}
    \small 智能书柜硬件结构建模（SolidWorks 设计）
\end{frame}

\begin{frame}{开发原型与硬件集成}
    \centering
    \includegraphics[width=\imgwidth]{prototype_hardware.png}
    \vspace{0.3cm}
    \small 开发原型配套图 - 硬件模块集成示意图
\end{frame}

% 继续搜索: \frametitle{软件闭环功能}
% 在该章节末尾插入 ISBN 相关图片
```

**Step 4: .md 文件同步**

在 .md 文件的对应章节中插入图片引用：

```markdown
## 二、项目内容（原型与技术指标）(2.5 min)

### 2.2 硬件终端原型

| 组件 | 规格参数 |
|------|----------|
| **机身规格** | 碳钢板结构 + 透明屏蔽玻璃，单柜 40-60 个独立格口（270×200×90mm/格） |
...

**🆕 硬件设计图**：
- SolidWorks 硬件结构设计：
  ![SolidWorks 设计图](b8f5b5fba769e1ae4ddad46b23847fc7.png)
- 开发原型配套图：
  ![原型硬件](image.png)

### 2.3 软件闭环功能

... 原有内容 ...

**🆕 ISBN 识别功能测试**：
| 识别成功案例 | ISBN 样例 |
|--------------|----------|
| ![案例](226a10bce9c554ec6ffd5f5b99c44834.jpg) | ![样例](image-1.png) |
```

#### B. 更新数据

对比并更新关键数据：
- 人名: `\author{...}` 中的内容
- 标题: `\title{...}` 中的内容
- 数据: 正文中的数字

#### C. 新增章节

在对应位置插入新的章节内容

#### D. 结构调整

根据 .md 的新结构重新排序

### 3.4 同步 .tex 文件

更新 `main.tex`（XeLaTeX + ctex 版本）中的变化部分。

---

## 转换规则

### 标题转换

```markdown
# 一级标题     →  \section{一级标题} + 章节页
## 二级标题    →  \frametitle{二级标题}
### 三级标题   →  \textbf{三级标题}
```

### 图片转换

```markdown
<img src="image.png" style="max-width: 70%;">
↓
\includegraphics[width=\imgwidth]{image.png}
```

### GIF / 视频转换

```markdown
![描述](demo.gif)
↓ (自动提取帧到 sources/demo/frame_0.png, frame_1.png, ...)
↓ (LaTeX preamble 需 \usepackage{animate})
\animategraphics[autoplay,loop,width=0.5\textwidth]{10}{sources/demo/frame_}{0}{N}
```

**关键注意事项**：
- `\animategraphics` 文件名编号**无前导零**: `frame_0.png`, `frame_1.png`（不是 `frame_00.png`）
- 帧率 = `1000 / gif_duration_ms`（GIF 默认 100ms/帧 → 10fps）
- PDF 体积与帧数成正比，建议单个动画 ≤ 120 帧
- **仅 Adobe Acrobat Reader 支持动画播放**，其他阅读器显示静态首帧

### 表格转换

```markdown
| 列1 | 列2 |
|-----|-----|
| A   | B   |
↓
\begin{tabular}{|c|c|}
\hline
列1 & 列2 \\
\hline
A & B \\
\hline
\end{tabular}
```

---

## 文件结构

```
<project_folder>/
├── <name>.md            # Markdown 主源文件
├── main.tex             # XeLaTeX + ctex 版本
├── main.pdf             # Beamer PDF (animate 动画, 需 Acrobat Reader)
├── gen_pptx.py          # python-pptx 生成脚本 (LLM 根据 .tex 自动生成)
├── main.pptx            # PPTX (GIF 原生动画, 全平台兼容, 精美排版)
└── sources/             # 图片目录
    ├── image1.png
    ├── demo.gif         # GIF 原文件 (PPTX 直接嵌入)
    ├── demo/            # GIF 帧目录 (PDF animate 用)
    │   ├── frame_0.png
    │   └── ...
    └── ...
```

---

## 同步报告

每次同步后输出报告：

```
## 同步完成

### 检测到的变化:
✅ 新增图片: solidworks_structure.png
✅ 新增图片: prototype_hardware.png
✅ 新增图片: isbn_recognition.jpg
✅ 新增图片: isbn_sample.png

### 更新的文件:
✅ docs/documentation/项目分享答辩框架.md
   - 添加图片引用（4张）
   - 添加更新日志
✅ main.tex
   - 新增 3 个页面

### 新增页面:
- 第 13 页: SolidWorks 硬件结构设计
- 第 14 页: 开发原型与硬件集成
- 第 14.5 页: ISBN 识别功能测试

### .md 文件同步状态:
✅ 图片引用已添加到文件顶部
✅ 更新日志已添加到文件末尾
✅ 人名信息已确认一致
✅ 项目名称已确认一致
```

### .md 文件更新示例

**更新前**：
```markdown
# "清园书享"项目分享答辩框架

**总时长**: 约 7-8 分钟
...
```

**更新后**：
```markdown
SolidWorks 硬件结构图
![alt text](b8f5b5fba769e1ae4ddad46b23847fc7.png)

开发原型配套图，放入硬件的地方
![alt text](image.png)

测试ISBN识别成功案例
![alt text](226a10bce9c554ec6ffd5f5b99c44834.jpg)

ISBN样例
![alt text](image-1.png)

# "清园书享"项目分享答辩框架

**总时长**: 约 7-8 分钟
...

---

## 更新日志

### 2025-04-16
- 新增 SolidWorks 硬件结构设计图
- 新增开发原型配套图
- 新增 ISBN 识别功能测试截图
- 同步更新团队信息（洪誌慧、李佳昊、潘洪浩）
```

---

## Step 4: MiKTeX 编译生成 PDF

**每次生成或更新 .tex 后，必须调用 MiKTeX 编译为 PDF。**

### 4.1 编译命令

```bash
# 进入工作目录
cd <folder_path>

# XeLaTeX 编译（推荐）
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex  # 第二遍，生成正确目录
```

### 4.2 编译后重叠检测（必须执行）

**每次编译后，必须检查 Overfull 警告并修复，直到无内容溢出。**

```bash
# 检测垂直溢出（内容超出页面高度，导致可见重叠）
xelatex -interaction=nonstopmode main.tex 2>&1 | grep "Overfull \\\\vbox"

# 检测水平溢出（表格/图片超出页面宽度）
xelatex -interaction=nonstopmode main.tex 2>&1 | grep "Overfull \\\\hbox"
```

#### 判断规则

| 警告类型 | 严重程度 | 含义 | 处理方式 |
|---------|---------|------|---------|
| `Overfull \vbox` | **严重** | 内容超出页面高度，页面间内容重叠 | **必须修复** |
| `Overfull \hbox` (固定值，每页都有) | 无害 | frametitle 装饰线条的全宽 `\rule{\paperwidth}` | 忽略 |
| `Overfull \hbox` (变化值) | 需修复 | 表格/图片/代码框超出文本宽度 | 用 `adjustbox` 或缩小尺寸 |

#### 自动修复流程

```python
# 编译后自动执行以下检测和修复循环
while True:
    warnings = check_overfull("main.tex")  # 编译并提取警告

    vbox_issues = [w for w in warnings if "Overfull \\vbox" in w]
    hbox_issues = [w for w in warnings if "Overfull \\hbox" in w and not is_frametitle_rule(w)]

    if not vbox_issues and not hbox_issues:
        break  # 无重叠，完成

    # 修复 vbox 溢出（内容太多）
    for issue in vbox_issues:
        fix_vbox_overflow(issue)  # 缩小字号、减少内容、压缩间距

    # 修复 hbox 溢出（内容太宽）
    for issue in hbox_issues:
        fix_hbox_overflow(issue)  # 用 adjustbox 包裹表格、缩小图片宽度
```

#### 常见修复手法

**vbox 溢出（内容太高）**：
1. 减小字号：`\small` → `\scriptsize` → `\tiny`
2. 压缩列表间距：`\begin{itemize}\setlength{\itemsep}{1pt}`
3. 减少 `\vspace` 间距
4. 拆分内容到两页
5. 减少表格行数（只保留关键行）

**hbox 溢出（内容太宽）**：
1. 用 `adjustbox` 包裹表格：
   ```latex
   \usepackage{adjustbox}
   \begin{adjustbox}{max width=\textwidth}
     \begin{tabular}{...} ... \end{tabular}
   \end{adjustbox}
   ```
2. 缩小图片宽度：`width=0.9\textwidth` → `width=0.8\textwidth`
3. 减少 `columns` 宽度总和（不超过 0.96\textwidth）
4. 代码框使用 `breaklines=true`

**识别无害的 hbox（frametitle 装饰线）**：
- 如果 `Overfull \hbox` 的值在所有页面都相同（如 56.9pt），且出现在 `\end{frame}` 行
- 这来自 frametitle 模板中的 `{\color{nvgreen}\rule{\paperwidth}{2pt}}`
- **这是设计预期**，不需要修复

### 4.3 编译后清理辅助文件（可选）

```bash
rm -f *.aux *.log *.out *.toc *.nav *.snm *.vrb *.fls *.fdb_latexmk *.synctex.gz
```

### 4.4 工作区文件结构

同一文件夹管理同名文件：

```
<project_folder>/
├── <name>.md            # Markdown 源文件
├── main.tex             # XeLaTeX + ctex 版本
├── main.pdf             # 编译输出的 PDF
├── gen_pptx.py          # python-pptx 生成脚本 (LLM 根据 .tex 自动生成)
├── main.pptx            # 精美 PPTX (复刻 Beamer 排版)
└── sources/             # 图片目录
    ├── image1.png
    └── ...
```

### 4.5 打开文件夹（/latex-beamer <path>）

当用户提供文件夹路径时：

1. **扫描目录** — 列出 .MD / .tex / .pdf / .pptx 文件和 sources/ 图片
2. **判断状态**:
   - 有 .MD 但无 .tex → 走 Step 2 完整生成 + 编译
   - 有 .tex 但无 .pdf → 走 Step 4 编译
   - .MD 比 .tex 新 → 走 Step 3 增量同步 + 编译
   - 三者都有且 .tex 最新 → 提示"已是最新"
3. **`--pptx` 路由**:
   - 用户传入 `--pptx` → 跳过 Step 2/3/4，直接走 **Step 5**（读取 .tex → gen_pptx.py → 执行）
   - 有 .tex 无 .pdf + `--pptx` → 不编译 PDF，直接生成 PPTX
   - 无 .tex + `--pptx` → 先走 Step 2 生成 .tex（不编译），再走 Step 5
4. **执行对应步骤** → 生成/同步 + 编译 + 生成 PPTX

---

## Step 5: python-pptx 生成精美 PPTX（复刻 Beamer 排版）

**在 Step 4 (PDF 编译) 完成后，LLM 读取 .tex 结构，生成 python-pptx 脚本复刻同一布局。**

### 5.1 为什么需要 PPTX

| 特性 | PDF (Beamer) | PPTX (python-pptx) |
|------|-------------|-------------------|
| GIF 动画 | 仅 Acrobat Reader | 所有环境原生播放 |
| 主题样式 | 精美自定义 | LLM 复刻 Beamer 排版 |
| 数学公式 | 完美支持 | 文本近似 |
| 表格 | 完美支持 | 完美支持 |
| 编辑性 | 不可编辑 | 可自由编辑 |

### 5.2 核心原理

**没有 LaTeX→PPTX 自动转换库。** PPTX 的精美排版靠以下流程实现：

```
.tex 文件 → LLM 读取并理解结构 → 生成 gen_pptx.py → python-pptx 执行 → .pptx
```

1. LLM 读取 `main.tex` 的完整内容
2. 解析每页 `\begin{frame}` 的结构：标题、分栏 `\begin{columns}`、block、图片、表格
3. 生成 `gen_pptx.py` 脚本，用 python-pptx 精确复刻每个元素的位置、颜色、内容
4. 执行脚本生成 `main.pptx`

### 5.3 LLM 解析 .tex 的规则

LLM 读取 .tex 时，提取以下结构信息：

#### 解析目标

```python
# 每个 frame 提取:
frame = {
    "title": r"\begin{frame}{标题}",          # 页面标题
    "plain": True/False,                       # 是否 plain 页（无标题栏）
    "columns": [                               # 分栏布局
        {
            "width": "0.50",                   # 栏宽比例
            "blocks": [                        # Beamer block
                {"title": "...", "items": [...]}
            ],
            "images": [                        # 图片
                {"path": "sources/xxx.png", "width": 0.95}
            ],
            "tables": [...],                   # 表格数据
            "animate": [                       # animategraphics 动画
                {"base": "sources/demo/frame_", "start": 0, "end": 66, "fps": 10}
            ],
            "text": [...]                      # 自由文本
        }
    ]
}
```

#### 排版映射规则

| Beamer 元素 | python-pptx 对应 |
|-------------|-----------------|
| `\begin{frame}` | `add_blank_slide()` |
| 标题栏 `\frametitle{}` | 深蓝矩形 + 白色文字 + 绿色分隔线 |
| `\begin{columns}` | 左右分区放置元素 |
| `\begin{block}{标题}` | 绿色圆角标题条 + 灰色圆角正文 |
| `\begin{alertblock}` | 橙色圆角标题条 + 浅橙正文 |
| `\includegraphics` | `slide.shapes.add_picture()` |
| `\animategraphics` | `add_picture(.gif)` (PPTX 原生动画) |
| `\begin{tabular}` | 手动绘制表格行（文本框对齐） |
| `\begin{itemize}` | 列表项，每项一行 |
| `\begin{tikzpicture}` | 用圆角矩形 + 文字 + 箭头复刻 |
| `frame[plain]` | 全屏背景色 + 居中内容 |

#### 颜色方案（从 .tex 提取）

```python
# 从 .tex 的 \definecolor 提取，或使用默认值
DEFAULT_COLORS = {
    "dkblue":  RGBColor(0, 60, 113),     # 标题栏、框架
    "nvgreen": RGBColor(118, 185, 0),     # block 标题、分隔线
    "lgray":   RGBColor(240, 240, 240),   # block 正文背景
    "white":   RGBColor(255, 255, 255),
    "red":     RGBColor(200, 50, 50),     # 警告、失败标记
    "gray":    RGBColor(120, 120, 120),   # 说明文字
}
```

### 5.4 gen_pptx.py 脚本结构

LLM 生成的脚本必须包含以下标准结构：

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
import os

# ── 路径 ──
BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "sources")

# ── 颜色（从 .tex 提取） ──
DKBLUE = RGBColor(...)
NVGREEN = RGBColor(...)
# ...

# ── 工具函数（固定，不需要 LLM 修改） ──
def add_blank_slide(prs): ...
def add_rect(slide, left, top, w, h, color): ...
def add_rounded_rect(slide, left, top, w, h, color): ...
def add_textbox(slide, left, top, w, h, text, ...): ...
def add_title_bar(slide, title): ...
def add_block(slide, left, top, w, h, title, items, ...): ...
def add_image_safe(slide, path, left, top, ...): ...

# ── 16:9 尺寸 ──
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# ── 页面 1~N（LLM 根据 .tex 每页内容生成） ──
# Slide 1: ...
# Slide 2: ...
# ...

# ── 保存 ──
prs.save(os.path.join(BASE, "main.pptx"))
```

### 5.5 执行命令

```bash
<LOCAL_USER>/AppData/Local/Programs/Python/Python314/python.exe gen_pptx.py
```

**注意**：
- 如果 `main.pptx` 被 PowerPoint 打开，会 PermissionError，此时输出为 `main_v2.pptx`
- GIF 文件直接用 `add_picture()` 嵌入，PowerPoint 会自动播放动画
- 每次 .tex 内容变化后，需重新生成 `gen_pptx.py` 并执行

### 5.6 何时重新生成 PPTX

| 触发条件 | 动作 |
|---------|------|
| .tex 首次生成 | 生成 gen_pptx.py + 执行 |
| .tex 内容变化（增删页、改内容） | 重新生成 gen_pptx.py + 执行 |
| .tex 仅样式变化 | 通常不需要改 gen_pptx.py |
| sources/ 中图片变化 | 仅重新执行 gen_pptx.py |

### 5.7 最终文件结构

```
<project_folder>/
├── <name>.md            # Markdown 主源文件
├── main.tex             # XeLaTeX + ctex 版本
├── main.pdf             # Beamer PDF（animate 动画，需 Acrobat Reader）
├── gen_pptx.py          # python-pptx 生成脚本（LLM 根据 .tex 自动生成）
├── main.pptx            # PPTX（GIF 原生动画，全平台兼容，精美排版）
└── sources/             # 图片目录
    ├── image1.png
    ├── demo.gif         # GIF 原文件（PPTX 直接嵌入）
    ├── demo/            # GIF 帧目录（PDF animate 用）
    │   ├── frame_0.png
    │   └── ...
    └── ...
```

### 5.8 输出选择建议

- **现场投屏演示** → 用 `.pptx`（GIF 动画全平台兼容，可编辑）
- **学术答辩 / 精美排版** → 用 `.pdf`（Beamer 原生，LaTeX 公式完美）
- **两者都生成** → 保留 `.md` 作为唯一源文件，同时输出 PDF + PPTX

---

## Usage Examples

- "/latex-beamer" — 打开当前目录，扫描并处理
- "/latex-beamer docs/presentation/templates/latex/智绘晚晴AR眼镜" — 打开指定文件夹
- "同步 LaTeX" — 检测并同步变化
- "更新幻灯片" — 根据 .md 更新 .tex
- "生成 LaTeX" — 完整生成新文件
- "/latex" — 执行智能同步
- "/latex-beamer --pptx" — 仅生成 PPTX（跳过 PDF 编译）
- "/latex-beamer --pptx path/to/folder" — 指定路径，仅生成 PPTX
- "/latex-beamer --pptx path/to/slides.tex" — 从指定 .tex 文件直接生成 PPTX

---

## Dependencies

- **MiKTeX** — `C:\MiKTeX\miktex\bin\x64\` (xelatex)
- **xelatex** — 编译 ctex 版本（支持中英文、生僻字）
- **python-pptx** — `pip install python-pptx` (LLM 生成 gen_pptx.py 复刻 Beamer 排版)
- **Pillow** — `pip install Pillow` (GIF 帧提取，PDF animate 用)
- **Python 3.14** — `<LOCAL_USER>/AppData/Local/Programs/Python/Python314/python.exe`
- **在线编译**: Overleaf（将 Compiler 设为 XeLaTeX 即可）
