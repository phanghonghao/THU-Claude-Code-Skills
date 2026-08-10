---
name: web-search-fallback
description: >
  Local zero-MCP web search & URL reader. Use as the automatic fallback whenever
  MCP web_search / webReader tools hit rate limits (429 errors, quota exhausted),
  or proactively for academic/GitHub queries. Routes queries to: arXiv API,
  GitHub API (gh CLI / curl), Semantic Scholar API, and direct curl page fetch.
  Trigger when: user mentions 搜论文/查论文/find papers/arxiv/github search,
  OR when you see "MCP error -429" / "Weekly/Monthly Limit Exhausted" /
  "webReader_result_summary" with error text.
triggers:
  - MCP error -429
  - Weekly/Monthly Limit Exhausted
  - webReader_result_summary
  - rate limit exhausted
  - 搜论文
  - 查论文
  - 搜索论文
  - find papers
  - search arxiv
  - arxiv search
  - semantic scholar
  - github search
  - 搜github
  - 查开源
  - alternative search
  - zhihu
  - 知乎
  - zhuanlan.zhihu.com
---

# Web Search Fallback — 零 MCP 额度的本地搜索/阅读

当 MCP `web_search` / `webReader` 工具返回 **429 限流错误**（`MCP error -429` / `Weekly/Monthly Limit Exhausted`）时，**立即切换到本 skill 的本地方案**，不要重试 MCP。

也适用于：用户主动要求搜论文、搜 GitHub、读网页，且不想消耗 MCP 额度时。

---

## 路由决策表

| 用户意图 | 路由 | 工具 |
|---------|------|------|
| 搜学术论文 | **Route 1: arXiv API** | `curl` + `python` XML 解析 |
| 搜 GitHub 仓库 | **Route 2: GitHub API** | `gh search repos` 或 `curl` REST API |
| 论文引用/关联图谱 | **Route 3: Semantic Scholar** | `curl` JSON API |
| 读特定 URL 内容 | **Route 4: 直接 curl 抓取** | `curl -sL` + 文本提取 |
| 读知乎专栏文章 | **Route 4b: 知乎 / Jina Reader** | `curl https://r.jina.ai/<url>` |
| 通用网络搜索 | **Route 5: DuckDuckGo HTML** | `curl` + grep（兜底，质量有限） |

**Windows 注意**: 用 `python` 而非 `python3`（Windows App Execution Alias 会拦截 `python3`）。

---

## Route 1: arXiv API（学术论文搜索）

### 基础搜索
```bash
curl -sL --max-time 25 "http://export.arxiv.org/api/query?search_query=all:KEYWORD1+AND+all:KEYWORD2&start=0&max_results=10&sortBy=submittedDate&sortOrder=descending" | python -c "
import sys,xml.etree.ElementTree as ET
ns={'a':'http://www.w3.org/2005/Atom'}
root=ET.parse(sys.stdin).getroot()
for e in root.findall('a:entry',ns):
    t=e.find('a:title',ns).text.strip().replace('\n',' ')
    d=e.find('a:published',ns).text[:10]
    aid=e.find('a:id',ns).text.split('/')[-1]
    s=e.find('a:summary',ns).text.strip().replace('\n',' ')[:200]
    print(f'{d} | {aid} | {t}')
    print(f'  {s}...')
    print()
"
```

### 搜索语法
- `all:keyword` — 全文搜索
- `ti:keyword` — 仅标题
- `au:keyword` — 仅作者
- 布尔: `+AND+`, `+OR+`, `+AND+NOT+`
- 精确短语: `%22reward+design%22`（URL 编码的引号）
- 排序: `sortBy=submittedDate|relevance|lastUpdatedDate` & `sortOrder=ascending|descending`

### 示例：搜 reward design + LLM
```bash
curl -sL --max-time 25 "http://export.arxiv.org/api/query?search_query=all:%22reward+design%22+AND+all:%22large+language+model%22&max_results=12&sortBy=submittedDate&sortOrder=descending"
```

### 按 arxiv ID 取全文摘要
```bash
curl -sL --max-time 25 "http://export.arxiv.org/api/query?id_list=2310.12931" | python -c "
import sys,xml.etree.ElementTree as ET
ns={'a':'http://www.w3.org/2005/Atom'}
root=ET.parse(sys.stdin).getroot()
e=root.find('a:entry',ns)
print(e.find('a:title',ns).text.strip())
print(e.find('a:summary',ns).text.strip())
"
```

---

## Route 2: GitHub 搜索

### 用 gh CLI（已认证，推荐）
```bash
gh search repos "KEYWORD" --sort stars --limit 10
gh search repos "reward design LLM" --sort stars --limit 10
gh search code "function_name" --language python --limit 10
```

### 用 GitHub REST API（无需认证，60 req/hr）
```bash
curl -s "https://api.github.com/search/repositories?q=KEYWORD+language:python&sort=stars&per_page=10" | python -c "
import sys,json
d=json.load(sys.stdin)
for r in d.get('items',[]):
    print(f\"{r['stargazers_count']:>6}⭐  {r['full_name']}\")
    desc = r.get('description','') or ''
    print(f'      {desc[:80]}')
    print(f'      {r[\"html_url\"]}')
    print()
"
```

### 获取仓库 README
```bash
gh api repos/OWNER/REPO/readme --jq '.content' | base64 -d
# 或
curl -sL "https://raw.githubusercontent.com/OWNER/REPO/main/README.md"
```

---

## Route 3: Semantic Scholar（论文关联图谱）

### 按关键词搜论文（含引用数）
```bash
curl -sL --max-time 20 "https://api.semanticscholar.org/graph/v1/paper/search?query=reward+design+LLM&limit=10&fields=title,year,citationCount,abstract,url" | python -c "
import sys,json
d=json.load(sys.stdin)
for p in d.get('data',[]):
    print(f\"{p.get('year','?')} | {p.get('citationCount',0):>5} cites | {p['title']}\")
    ab = p.get('abstract','') or ''
    print(f'  {ab[:150]}...')
    print()
"
```

### 按论文 ID 查引用/被引
```bash
# 引用了哪些论文
curl -sL "https://api.semanticscholar.org/graph/v1/paper/ARXIV:2310.12931/references?limit=10&fields=title,year"
# 被哪些论文引用
curl -sL "https://api.semanticscholar.org/graph/v1/paper/ARXIV:2310.12931/citations?limit=10&fields=title,year"
```

---

## Route 4: 直接 curl 抓取网页

适用于已知 URL，提取文本内容（无 JS 渲染）。JS 渲染页（知乎、SPA 等）走 **Route 4b**。

```bash
# 抓取并转为纯文本（去 HTML 标签）
curl -sL --max-time 20 "https://example.com/page" | sed 's/<[^>]*>//g' | sed '/^\s*$/d' | head -100

# 抓取项目主页（项目页通常是静态 HTML）
curl -sL "https://eureka-research.github.io/" | sed 's/<[^>]*>//g' | sed '/^\s*$/d'

# 抓取 GitHub raw 文件
curl -sL "https://raw.githubusercontent.com/NVlabs/Eureka/main/README.md"
```

### 论文 PDF 的处理
arxiv PDF 无法直接 curl 解析，但可以：
1. 用 arxiv API 取摘要（Route 1）
2. 用 Semantic Scholar 取摘要（Route 3）
3. 提示用户用 `/pdf-reader` skill 读本地下载的 PDF

---

## Route 4b: 知乎专栏 / 通用 JS 渲染页面（Jina Reader）

知乎对 curl / 普通 UA 返回 403，且是 JS 渲染页，Route 4 的 `curl` + `sed` 抓不到正文。
用 Jina Reader 代理 `https://r.jina.ai/<目标URL>`，免费、无需 key、返回干净的 Markdown。

```bash
curl -sL --max-time 60 "https://r.jina.ai/https://zhuanlan.zhihu.com/p/<ARTICLE_ID>" -o /tmp/article.md
```

**注意（Windows/Git Bash）**：`/tmp` 实际在 `D:\Users\<user>\AppData\Local\Temp\`。用 `cygpath -w` 拿到 Windows 绝对路径后再用 Read 工具读取：
```bash
cygpath -w /tmp/article.md
```

### 产物整理（重要）

抓到的 Markdown 头几行是 Jina 的元数据（`Title:` / `URL Source:` / `Markdown Content:`），**写入正式文件前删除这几行**，只保留正文。

知乎正文里大量指向 `zhida.zhihu.com/search?content_id=...&zd_token=...` 的词条自链：
- 这些链接是**会话级 token，会过期**，长期保存没有价值；
- 写入 Markdown 时应**还原为纯文本词条**（去掉 `[词条](url)` 链接包装），保留**真正的站外链接**（arxiv、GitHub、`link.zhihu.com/?target=...` 外链、其它专栏文章）；
- 图片 `![Image N](https://pica.zhimg.com/...)` 保留原 URL，图片不下载。

### 替代方案

- 网页版知乎 `zhuanlan.zhihu.com` 走不通时，可尝试 `zhihu.com/question/<id>` 镜像与移动端 `zhuanlan.zhihu.com/p/<id>`（HTTPS 升级后若 403，退回 r.jina.ai）。
- Jina 偶尔限流，可重试一次；仍失败则告诉用户 /web-search-fallback 免费路线拿不到该页面，建议浏览器手动复制。

---

## Route 5: DuckDuckGo（通用搜索兜底）

质量有限，仅在上述路由都不适用时使用。

```bash
# DuckDuckGo Instant Answer API（结构化，但覆盖面窄）
curl -sL "https://api.duckduckgo.com/?q=KEYWORD&format=json&no_html=1" | python -c "
import sys,json
d=json.load(sys.stdin)
print(d.get('Abstract','(no instant answer)'))
for r in d.get('RelatedTopics',[])[:5]:
    if isinstance(r,dict) and 'Text' in r:
        print(f'- {r[\"Text\"][:100]}')
"

# DuckDuckGo HTML（提取链接，非结构化）
curl -sL "https://html.duckduckgo.com/html/?q=KEYWORD" | grep -oP 'https?://[^"<>]+' | grep -v duckduckgo | head -10
```

---

## 自动降级流程

```
用户要搜索/阅读
    │
    ├─ 先试 MCP web_search / webReader（如果额度充足）
    │
    ├─ MCP 返回 429 / "Limit Exhausted"？
    │     │
    │     ▼ YES → 切换到本 skill
    │     ┌─────────────────────────────┐
    │     │ 判断查询类型：               │
    │     │  学术论文 → Route 1 (arXiv)  │
    │     │  GitHub  → Route 2 (gh/API)  │
    │     │  论文关系 → Route 3 (S2)     │
    │     │  读网页   → Route 4 (curl)   │
    │     │  读知乎   → Route 4b (Jina)  │
    │     │  通用搜索 → Route 5 (DDG)    │
    │     └─────────────────────────────┘
    │
    └─ 不确定类型？先 Route 1 + Route 2 并行试，取最优结果
```

**核心规则**：检测到 MCP 429 错误后，**不要重试 MCP**，直接走本地路由。

---

## 常见用法示例

### "帮我搜 reward design 相关论文"
→ Route 1 (arXiv) + Route 3 (Semantic Scholar) 并行

### "找 Eureka 的 GitHub 仓库和代码"
→ Route 2 (gh search) + Route 4 (curl README)

### "这篇论文被哪些论文引用了"
→ Route 3 (Semantic Scholar citations)

### "读一下这个项目主页"
→ Route 4 (curl + sed 去 HTML 标签)

### "抓取这篇知乎文章全文存成 .md"
→ Route 4b (Jina Reader)，清理元数据头与 zhida 自链后写入目标文件

---

## 限制说明

- **无法做真正的 Google/Bing 搜索** — 没有免费无限制的通用搜索 API。Route 5 (DuckDuckGo) 质量有限。
- **无法渲染 JS 页面** — curl 只拿静态 HTML。SPA 网站可能拿不到内容。**知乎等 JS 站请用 Route 4b (Jina Reader)。**
- **arXiv 覆盖学术预印本** — 不含期刊专属或非 arXiv 论文。配 Semantic Scholar 补全。
- **Windows 用 `python` 不是 `python3`** — App Execution Alias 会拦截 python3。
