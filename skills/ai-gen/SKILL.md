---
name: ai-gen
description: "AI 生图/生视频。通过 paratera API 生成图片和视频。Use when user mentions: ai-gen, 生图, 生视频, 文生图, 文生视频, 生成图片, 生成视频, AI绘图, AI视频, AI生图, AI生视频, image generation, video generation, 批量生图, 批量生视频."
---

# AI-Gen Skill - AI 生图/生视频 (多模型组合版)

通过 paratera API 进行文生图和文生视频生成。支持三个模型预设（豆包/GLM/MiniMax），可跨系列组合补齐能力。

## 可用预设

| 预设 | Provider | 文生图 | 文生视频 | 说明 |
|------|----------|--------|---------|------|
| 豆包 (默认) | `doubao` | GLM-CogView3-Flash | Doubao-Seedance-1.0-Pro | 豆包图挂了，用 GLM 补 |
| GLM | `glm` | GLM-CogView3-Flash | Doubao-Seedance-1.0-Pro | GLM 无视频，用豆包补 |
| MiniMax | `minimax` | GLM-CogView3-Flash | MiniMax-T2V-01-Directo | MiniMax 无图，用 GLM 补 |

> 三个预设的图片都是 GLM（唯一可用的图片模型），区别在视频模型。

## 完整工作流程

### Step 1: 获取输入

询问用户提供 .MD 文件路径或直接描述生成需求：

```
请提供要生成的 .MD 文件路径，或直接描述你想生成的图片/视频内容。
```

### Step 2: 读取并分析文件

如果用户提供了 .MD 文件：
1. 使用 Read 工具读取文件内容
2. 分析文件中的场景描述、段落标题、关键画面
3. 将内容拆分为可独立生成的场景/描述项

如果用户直接描述需求：
1. 分析用户描述
2. 将其拆分为合理的生成任务

### Step 3: 选择模型预设

使用 AskUserQuestion 让用户选择预设：

```
问题: "请选择模型预设："
Header: "模型预设"
选项:
  a. 豆包 (Doubao) — 视频: Doubao-Seedance-1.0-Pro (推荐)
  b. GLM — 视频: Doubao-Seedance-1.0-Pro (同豆包视频)
  c. MiniMax — 视频: MiniMax-T2V-01-Directo
```

图片统一使用 GLM-CogView3-Flash（无需选择）。

### Step 4: 制定生成计划

将分析结果整理为结构化的生成计划表格，展示给用户：

```
## 生成计划 (预设: 豆包)

| # | 类型 | Prompt | 参数 |
|---|------|--------|------|
| 1 | 文生图 | A cute robot waving in a futuristic city | size=1024x1024 |
| 2 | 文生视频 | A robot walking through a neon-lit corridor | ratio=16:9 |
| ... | ... | ... | ... |

共计 N 项生成任务。
```

对每一项标注：
- **类型**: 文生图 (image) 或 文生视频 (video)
- **Prompt**: 英文提示词（如果原文是中文，翻译为英文，因为模型对英文 prompt 效果更好）
- **参数**: size / ratio / dur 等可选参数

### Step 5: 用户确认

展示计划后，询问用户确认：

```
以上生成计划是否满意？可以：
- 直接确认执行
- 修改某一项的 prompt / 参数
- 删除某些项
- 添加新项
```

### Step 6: 执行生成

用户确认后，按计划逐项调用 `generate.py` 执行生成。

对于每项任务，使用 Bash 工具执行：

**文生图:**
```bash
python "<LOCAL_USER>/.claude/skills/ai-gen/generate.py" --mode image --prompt "..." --provider <provider> --output "ai_gen_output/001_image.png"
```

**文生视频:**
```bash
python "<LOCAL_USER>/.claude/skills/ai-gen/generate.py" --mode video --prompt "..." --provider <provider> --output "ai_gen_output/002_video.mp4"
```

注意：
- 文生图是同步调用，约 10-30 秒返回
- 文生视频是异步调用（提交→轮询→下载），可能需要 2-5 分钟
- 多个文生图任务可以并行执行
- 文生视频建议串行以避免 API 限流
- API Key 池会自动轮换，无需手动指定 key

### Step 7: 输出结果

生成完成后，列出所有输出文件路径：

```
## 生成完成

| # | 类型 | 输出文件 | 状态 |
|---|------|----------|------|
| 1 | 文生图 | ai_gen_output/001_image.png | 成功 |
| 2 | 文生视频 | ai_gen_output/002_video.mp4 | 成功 |

所有文件保存在: ai_gen_output/
```

## 参数参考

### 文生图参数

| 参数 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| size | 1024x1024, 1536x1024, 1024x1536 | 1024x1024 | 图片尺寸 (宽x高) |

### 文生视频参数

**豆包 (doubao/glm):**

| 参数 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| ratio | 16:9, 9:16, 1:1, adaptive | 16:9 | 视频宽高比 |
| dur | 5, 10 | 5 | 视频时长 (秒) |

**MiniMax:**

MiniMax 视频不支持 ratio/dur 参数（由模型自动决定）。

## 直接使用模式

用户也可以不提供 .MD 文件，直接描述需求：

```
/ai-gen 帮我生成一张赛博朋克风格的城市夜景图
/ai-gen 生成一个5秒的视频，内容是机器人在实验室里走动
/ai-gen 批量生成以下图片：1. 日出山水画 2. 未来城市 3. 太空站
```

此时跳过 Step 2，直接进入 Step 3 选择模型，然后 Step 4 制定计划。

## 错误处理

- 如果 config.json 不存在，提示用户创建（参考 config.example.json）
- 如果 API Key 失效，自动切换到下一个 key
- 如果所有 key 都失效，提示用户更新 config.json
- 如果生成超时，建议用户重试或更换 prompt
- 如果模型不可用 (500: No deployments)，建议用户切换到其他预设
