---
name: paper-repro
description: >
  论文「读懂 + 最小复现」一体化工具。输入 arXiv URL / arXiv ID / 关键词 / 本地 PDF，
  先用 /paper-html-onepage 出单页 HTML 总结（读懂论文），再用本 skill 的脚本找代码、
  分析完整复现要求、制定最小复现方案、生成并自动跑通最小规模实验、给出完整复现成本估算
  （对标 alphaXiv 的 autoarxiv）。触发：复现论文 / 跑论文 / paper repro / reproduce paper /
  autoarxiv / minimal reproduction / 最小复现 / 把这篇论文跑起来。
triggers:
  - 复现论文
  - 跑论文
  - 最小复现
  - paper repro
  - reproduce paper
  - autoarxiv
  - minimal reproduction
---

# paper-repro — 论文「总结 + 最小复现」

把一篇论文变成：**一页可读总结 + 一个能在本机跑通的最小复现 + 完整复现成本估算**。
编排 `/paper-html-onepage`（读懂）+ 本 skill 的复现脚本（跑通）。

## ⚠️ 安全约束（自动运行模式必备，优先于一切）

- **只跑最小规模**：限定步数/epoch（默认 ≤ 几百步）、限定时长（默认 ≤ 几分钟）。
- **隔离运行**：所有复现代码、数据、日志放进**单独子目录**，不污染其他项目。
- **禁止 sudo / 管理员权限**，禁止改系统环境变量、禁止写用户主目录之外。
- **网络三思**：允许浅克隆（`git clone --depth 1`）和小数据下载；**超过 ~200MB 的下载、需登录/付费的数据集、需 Kaggle/HF token 的资源，先问用户**，不要自动拉取。
- **不确定就不跑**：如果生成的代码看不清在干嘛、或需重型依赖（CUDA 专版、编译、root），只产出方案+脚本，不自动执行，把决定权交给用户。

## 输入解析（Stage 0）

接受四种输入，统一抽出 **arXiv ID + 标题 + 输出目录**：
- arXiv URL：`https://arxiv.org/abs/1706.03762` 或 `/pdf/...` → 抽 ID
- arXiv ID：`1706.03762`
- 关键词/标题：如 `Attention Is All You Need`
- 本地 PDF：`--pdf <path>`（复现阶段需要标题，从文件名/首页推断）

输出目录默认 `<用户当前工作目录>/<论文短名>_repro/`。

## 6 阶段编排流程

> 本 skill 是 **agent 驱动** 的：脚本（`scripts/`）只做查找/分析/解析等机械活，
> **论文级的代码改写由你（agent）按方法论完成**——因为每篇论文不同，无法写成单一固定脚本。
> 这与 `/web-search-fallback`「指令 + 可复用片段」的设计哲学一致。

### Stage A — 读懂论文（委派 /paper-html-onepage，不改它）

```bash
python "<SKILL_ROOT>\paper-html-onepage\scripts\paper_to_onepage_html.py" \
  --url "<arxiv_url>" --out "<outdir>/<name>_summary.html"
```
（关键词搜用 `--query`；本地 PDF 用 `--pdf`。）得到 `<name>_summary.html`。

### Stage B — 找代码（scripts/find_repo.py）

```bash
python "<SKILL_ROOT>\scripts\find_repo.py" "1706.03762" --top 6
# 加 --json 拿结构化结果
```
arXiv ID → 自动取标题 → GitHub 按标题搜（比搜裸 ID 召回高）。多个候选时**让用户确认**用哪个。
（PapersWithCode 公开 API 已废弃返回 HTML，故不用；GitHub+arXiv 已覆盖常见情况。）

### Stage C — 分析完整复现要求（scripts/analyze_repo.py）

```bash
python "<SKILL_ROOT>\scripts\analyze_repo.py" "<repo_url>" --json > analyze_report.json
```
免克隆（走 GitHub tree API + raw）读 README/依赖/训练入口/配置，grep 资源信号（n_gpu、deepspeed、
batch_size、epochs、数据集路径），产出 JSON 可行性报告：入口、依赖、GPU 需求、阻断项、建议的最小化覆盖项。

### Stage D — 制定最小复现方案（agent 推理）

综合 **analyze_report + 本机硬件**（CPU/单卡）制定降维裁剪方案。常见手段：
- **换小模型**：d_model/layer/head 全砍（如 512→64、6→2、8→2）
- **砍步数**：几百 epoch → 几百步
- **关多卡**：`num_processes=1`、关 DeepSpeed/accelerate、必要时上 LoRA 省 VRAM
- **去重型数据依赖**：WMT/私有数据集 → **合成任务**（序列复制/反转/排序），0 下载
- **明确要验证的核心论点**：不追求复现原始 SOTA 数字，只验证论文核心主张是否成立

把方案简述给用户（1 段话 + 一张「原文配置 vs 最小配置」对照表）。

### Stage E — 生成并自动运行（agent 写代码 + scripts/summarize_eval.py）

1. 按方案**新建/改写**最小复现代码（模型 + 数据 + 训练循环），放进隔离子目录。
   - 通用模板见 `templates/run.sh.template`；已验证可跑的参考实现见 `templates/reference/`
     （Attention Is All You Need 的 CPU 最小复现，29 秒收敛）。
   - 训练脚本要把指标按 step 写进 **CSV**（列名含 `loss` 和 `acc`，便于自动解析）。
2. 写 `run.sh`，**低风险时直接跑**（遵循上方安全约束：限步数/隔离/小下载）。
3. 跑完调通用解析器出结果：

```bash
python "<SKILL_ROOT>\scripts\summarize_eval.py" \
  --log train_log.csv --chart training_curve.png \
  --task "<论文短名> 最小复现" --acc-threshold 0.8
```
自动识别 loss/acc 列、出表格 + 曲线图 + **PASS/INCONCLUSIVE** 判定。
（PASS 条件：最优 acc ≥ 阈值，或 loss 下降 ≥ 50%；均可 `--acc-threshold/--loss-drop` 调。）

### Stage F — 汇总报告（scripts/cost_estimate.py + 综合）

```bash
python "<SKILL_ROOT>\scripts\cost_estimate.py" \
  --report analyze_report.json --params <approx_params>
```
给出完整复现成本（GPU-小时 + 本机可行性）。

**最终汇报给用户**，包含三块：
1. 单页总结：`<name>_summary.html` 路径
2. 最小复现结果：loss/acc、曲线图、PASS/INCONCLUSIVE 判定、关键产物路径
3. 完整复现成本：GPU-小时、本机是否可行、为什么走最小复现

## 各脚本速查

| 脚本 | 作用 | 关键参数 |
|---|---|---|
| `scripts/find_repo.py` | arXiv ID/标题 → GitHub 候选仓库 | `--top N` `--json` |
| `scripts/analyze_repo.py` | 仓库 → JSON 可行性报告 | `--json` |
| `scripts/cost_estimate.py` | 完整复现成本估算 | `--report <json>` `--params <n>` |
| `scripts/summarize_eval.py` | 训练日志 → 表格+曲线+判定 | `--log` `--chart` `--acc-threshold` |

所有脚本网络层均为 **requests → curl → 警告退出**，对齐 `/web-search-fallback`，MCP 限流时仍可用。
Windows 注意用 `python` 而非 `python3`。

## 复用清单（不重复造轮子）

- **/paper-html-onepage**（`…\paper-html-onepage\scripts\paper_to_onepage_html.py`）：Stage A 直接委派，不改。
- **/web-search-fallback**：脚本网络降级 + Route 1/2/4 写法的来源。
- **templates/reference/**：已验证可跑的 Transformer 最小复现，作回归基线与改写样板。

## 范围与限制（如实告知用户）

- **不保证复现原始 SOTA 数字**：目标是验证论文核心论点 + 估完整成本，不是 1:1 复现。
- 许多论文需**私有数据/专有环境/特定硬件**，可能连最小复现也跑不动——此时只交付总结 + 成本估算 + 复现方案，如实说明卡点。
- 网络依赖 GitHub/arXiv 公开 API（受速率限制，有 curl 降级）。
- 成本估算是**粗略启发式**，仅作量级参考。
