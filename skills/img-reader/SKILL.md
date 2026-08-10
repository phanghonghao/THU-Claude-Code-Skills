---
name: img-reader
description: "读取和分析本地图片文件，零 MCP 额度。3级自动降级：Read+PIL增强 → GLM-4V-Flash(免费API) → PaddleOCR(离线)。Use when user mentions: 看图, 读图, 分析图片, 识别图片, img, image, 看一下图片, 图片内容, 截图, screenshot, 照片, photo, 读取图片, image analysis, 明细表, BOM, OCR."
---

# Img-Reader - 本地图片读取（零 MCP 额度）

## 3 级自动降级流程

```
Tier 0: Read + PIL 增强（零依赖，已集成）
    │ 置信度低 ↓ 自动降级
Tier 1: GLM-4V-Flash（免费 API，联网，不消耗 MCP 额度）
    │ 联网失败 / 无 API Key ↓ 自动降级
Tier 2: PaddleOCR（离线，本地 OCR）
    │
    └──→ 输出结果（跑通即停，不浪费后续资源）
```

**核心规则：只要上一级跑通就停，失败才自动降级。不调用 MCP analyze_image。**

---

## Tier 0: Read + PIL 增强

### 普通模式（截图/照片/整体描述）
直接 Read：
```
Read(file_path="<absolute_path>")
```

### 增强模式（工程图/明细表/小字）
用 PIL 裁剪+放大+增强后再 Read：

```bash
PYTHONIOENCODING=utf-8 python -c "
from PIL import Image, ImageEnhance, ImageFilter
import sys, os

img_path = sys.argv[1]
zoom = int(sys.argv[2]) if len(sys.argv) > 2 else 5
region = sys.argv[3] if len(sys.argv) > 3 else None

img = Image.open(img_path).convert('RGB')
w, h = img.size

if region:
    coords = [float(x) for x in region.split(',')]
    img = img.crop((int(w*coords[0]), int(h*coords[1]), int(w*coords[2]), int(h*coords[3])))

out = img.resize((img.width * zoom, img.height * zoom), Image.LANCZOS)
out = out.filter(ImageFilter.SHARPEN)
out = ImageEnhance.Contrast(out).enhance(1.8)
out = ImageEnhance.Sharpness(out).enhance(2.0)

base = os.path.splitext(img_path)[0]
save_path = base + '_enhanced.png'
out.save(save_path)
print(save_path)
" "<INPUT_PATH>" "<ZOOM>" "<REGION>"
```

### 置信度判断

读取后评估：
- **高**：文字清晰，直接输出 `[置信度：高]`
- **中**：部分模糊，用 `(?)` 标记不确定项 `[置信度：中]`
- **低**：大量不可辨 → **自动降级到 Tier 1**，不问用户

---

## Tier 1: GLM-4V-Flash（免费 VLM API）

当 Tier 0 置信度低时，**自动调用**（不问用户）：

```bash
python "<LOCAL_USER>/.claude/skills/img-reader/vision_api.py" "<image_path>" "<prompt>"
```

**前提**：需要 `ZHIPU_API_KEY` 环境变量（免费注册 https://open.bigmodel.cn 获取）

### API Key 配置（三选一）
1. 环境变量：`set ZHIPU_API_KEY=xxx`
2. `.env` 文件：放在 `<LOCAL_USER>/.claude/skills/img-reader/.env`，内容 `ZHIPU_API_KEY=xxx`
3. 首次使用时提示用户注册并配置

### 安装依赖
```bash
python -m pip install zhipuai -q
```

### 特点
- **完全免费**（glm-4v-flash 免费额度）
- **不是 MCP** — Python 直接 HTTP 调用，不消耗 MCP 额度
- 中文 OCR 能力好
- 返回 JSON：`{"success": true, "result": "...", "provider": "glm-4v-flash"}`

### 失败时自动降级到 Tier 2
失败情况：无 API Key、网络不通、API 报错

---

## Tier 2: PaddleOCR（离线本地 OCR）

当 Tier 1 失败时，**自动降级**：

```bash
# 普通文字识别
python "<LOCAL_USER>/.claude/skills/img-reader/ocr_local.py" "<image_path>"

# 表格/明细表提取
python "<LOCAL_USER>/.claude/skills/img-reader/ocr_local.py" "<image_path>" --table

# 首次使用自动安装
python "<LOCAL_USER>/.claude/skills/img-reader/ocr_local.py" "<image_path>" --install
```

### 安装依赖（自动）
```bash
python -m pip install paddleocr paddlepaddle -q
```

### 特点
- **完全离线** — 无需联网、无需 API Key
- **中文 OCR 最强** — 百度 PP-OCRv4
- **表格识别** — PP-Structure 可提取 BOM/明细表
- 模型首次运行时自动下载（~100MB），之后离线可用
- 返回 JSON：`{"success": true, "full_text": "...", "text_lines": [...]}`

---

## Implementation Steps

### Step 1: 判断是否需要增强
- 普通图片 → 直接 Read（Tier 0 普通模式）
- 工程图/明细表/小字 → PIL 增强 + Read（Tier 0 增强模式）

### Step 2: 评估置信度
- 置信度高 → 直接输出，结束
- 置信度低 → **静默降级**到 Tier 1

### Step 3: 调用 Tier 1（GLM-4V-Flash）
- 如果成功 → 输出结果，结束
- 如果失败（无 Key / 无网络）→ **静默降级**到 Tier 2

### Step 4: 调用 Tier 2（PaddleOCR）
- 如果用户需求涉及表格/明细表 → 用 `--table` 模式
- 输出 OCR 结果，结束

### Step 5: 输出
- 最终结果末尾标注使用的是哪个 Tier：`[通过 Tier X 完成]`
- 如果全部失败，建议用户手动调用 MCP analyze_image

---

## Rules

1. **不调用 `mcp__4_5v_mcp__analyze_image`** — 全程零 MCP 额度
2. **跑通即停** — 高级 Tier 成功后不继续降级
3. **静默降级** — 不打断用户，自动从 Tier 0 → 1 → 2 尝试
4. **标注来源** — 结果末尾显示 `[通过 Tier X 完成]`
5. **路径必须是绝对路径**
6. **多图并行读取**提高效率
