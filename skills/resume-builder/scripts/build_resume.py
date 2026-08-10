#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_resume.py —— 简历数据(YAML/JSON) → 填充 HTML 模板 → resume.html

用法:
    python build_resume.py <数据文件.yaml|json> [--template classic_single] [--out resume.html]

模板 token 契约 (templates/classic_single.html):
    <!--HEADER--> <!--EDUCATION--> <!--WORK--> <!--PROJECTS--> <!--LAB-->
    <!--CLUBS_COMPETITIONS--> <!--SELF--> <!--SKILLS--> <!--SOCIAL-->
本脚本逐板块生成 HTML 片段并替换对应 token；无数据的板块自动消失。
WORK / SELF 为可选板块：工作经历 / 自我评价，数据为空时自动隐藏。
"""

from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"


# ---------- 工具 ----------
def esc(s) -> str:
    """HTML 转义，None/数字安全处理。"""
    if s is None:
        return ""
    return escape(str(s), quote=False)


def date_range(start, end) -> str:
    """'2023.09 – 至今'；只有一边时只显示那一边。"""
    s = esc(start)
    e = esc(end)
    if s and e:
        return f"{s} – {e}"
    return s or e


def render_entry_head(title: str, date: str) -> str:
    return (
        f'<div class="r-entry-head">'
        f'<span class="r-title">{esc(title)}</span>'
        f'<span class="r-date">{esc(date)}</span>'
        f"</div>"
    )


def section(title: str, body: str) -> str:
    if not body.strip():
        return ""
    return (
        f'<section class="r-section">'
        f'<h2 class="r-section-title">{title}</h2>'
        f'<div class="r-entries">{body}</div>'
        f"</section>"
    )


# ---------- 各板块 ----------
def render_header(p: dict) -> str:
    if not p:
        return ""
    name = esc(p.get("name_cn", ""))
    if not name:
        return ""
    name_html = f'<h1 class="r-name">{name}'
    en = p.get("name_en", "")
    if en and str(en).strip():
        name_html += f'<span class="en">{esc(en)}</span>'
    name_html += "</h1>"

    bits = []
    if p.get("phone"):
        bits.append(f"电话: {esc(p['phone'])}")
    if p.get("email"):
        bits.append(f"邮箱: {esc(p['email'])}")
    contact = f'<div class="r-contact">{"&nbsp;&nbsp;".join(bits)}</div>' if bits else ""

    address = ""
    if p.get("address"):
        address = f'<div class="r-address">地址: {esc(p["address"])}</div>'

    target = ""
    if p.get("target"):
        target = f'<div class="r-target"><strong>求职意向：</strong>{esc(p["target"])}</div>'

    # 可选附加信息行（如 性别 / 出生年月 / 民族 / 婚姻状况）；留空则不渲染。
    extra = ""
    if str(p.get("extra", "")).strip():
        extra = f'<div class="r-contact">{esc(p["extra"])}</div>'

    # 可选证件照（右上角）；由 build_resume.py 注入 _photo_data_uri（base64 data-URI）。
    photo_uri = str(p.get("_photo_data_uri", "")).strip()
    photo_html = f'<img class="r-photo" src="{photo_uri}" alt="">' if photo_uri else ""
    cls = "r-header r-has-photo" if photo_html else "r-header"

    return f'<header class="{cls}">{name_html}{contact}{extra}{address}{target}{photo_html}</header>'


def render_education(items) -> str:
    if not items:
        return ""
    out = []
    for e in items:
        if not isinstance(e, dict) or e.get("optional"):
            continue
        school = e.get("school", "")
        if not school:
            continue
        head = render_entry_head(school, date_range(e.get("start"), e.get("end")))

        major = esc(e.get("major", ""))
        sub = f'<div class="r-sub"><span>{major}</span>'
        if e.get("city"):
            sub += f'<span class="city">{esc(e["city"])}</span>'
        sub += "</div>"

        detail_bits = []
        if e.get("gpa"):
            detail_bits.append(esc(e["gpa"]))
        if e.get("courses"):
            detail_bits.append(esc(e["courses"]))
        detail = f'<div class="r-detail">{"&nbsp;&nbsp;".join(detail_bits)}</div>' if detail_bits else ""

        out.append(f'<div class="r-entry">{head}{sub}{detail}</div>')
    if not out:
        return ""
    return section("教育背景", "\n".join(out))


def render_bullets(item) -> str:
    """把 item['bullets'] 列表渲染成项目符号 <ul>；无则空串。"""
    bullets = item.get("bullets") if isinstance(item, dict) else None
    if not isinstance(bullets, list) or not bullets:
        return ""
    items_html = "".join(
        f"<li>{esc(str(b).strip())}</li>" for b in bullets if str(b).strip()
    )
    return f'<ul class="r-bullets">{items_html}</ul>' if items_html else ""


def render_projects(items) -> str:
    if not items:
        return ""
    out = []
    for p in items:
        if not isinstance(p, dict):
            continue
        name = p.get("name", "")
        if not name:
            continue
        head = render_entry_head(name, date_range(p.get("start"), p.get("end")))

        role = ""
        if str(p.get("role", "")).strip():
            role = f'<div class="r-role">{esc(p["role"])}</div>'

        # 描述行：desc：tech。details。（沿用原 .tex 的中文标点风格；任一为空自动省略）
        desc = str(p.get("desc", "")).strip()
        tech = str(p.get("tech", "")).strip()
        details = str(p.get("details", "")).strip()
        text = desc
        if tech:
            text = f"{text}：{tech}" if text else tech
        if details:
            text = f"{text}。{details}" if text else details
        detail = f'<div class="r-detail">{esc(text)}</div>' if text else ""

        # 项目符号要点列表（可选；与 desc 互不冲突，有则追加）
        bullets = render_bullets(p)

        out.append(f'<div class="r-entry">{head}{role}{detail}{bullets}</div>')
    if not out:
        return ""
    return section("核心科研与项目经历", "\n".join(out))


def render_lab(items) -> str:
    if not items:
        return ""
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        name = it.get("name", "")
        if not name:
            continue
        head = render_entry_head(name, date_range(it.get("start"), it.get("end")))
        desc = ""
        if str(it.get("desc", "")).strip():
            desc = f'<div class="r-detail">{esc(it["desc"])}</div>'
        bullets = render_bullets(it)
        out.append(f'<div class="r-entry">{head}{desc}{bullets}</div>')
    if not out:
        return ""
    return section("实验室经历", "\n".join(out))


def render_work(items) -> str:
    """工作经历：单位 + 日期 + (可选) 职位 role + (可选) desc + bullets。"""
    if not items:
        return ""
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        name = it.get("name", "")
        if not name:
            continue
        head = render_entry_head(name, date_range(it.get("start"), it.get("end")))
        role = ""
        if str(it.get("role", "")).strip():
            role = f'<div class="r-role">{esc(it["role"])}</div>'
        desc = ""
        if str(it.get("desc", "")).strip():
            desc = f'<div class="r-detail">{esc(it["desc"])}</div>'
        bullets = render_bullets(it)
        out.append(f'<div class="r-entry">{head}{role}{desc}{bullets}</div>')
    if not out:
        return ""
    return section("工作经历", "\n".join(out))


def render_self(se) -> str:
    """自我评价：支持 字符串(整段) / 列表(要点) / {points:[...]} 三种写法。"""
    if se is None:
        return ""
    points = None
    para = ""
    if isinstance(se, str):
        para = se.strip()
    elif isinstance(se, list):
        points = [str(x).strip() for x in se if str(x).strip()]
    elif isinstance(se, dict):
        raw = se.get("points")
        if isinstance(raw, list):
            points = [str(x).strip() for x in raw if str(x).strip()]
        if not points:
            para = str(se.get("desc", "")).strip()
    else:
        return ""
    if points:
        items_html = "".join(f"<li>{esc(p)}</li>" for p in points)
        body = f'<ul class="r-bullets">{items_html}</ul>'
    elif para:
        body = f'<div class="r-detail">{esc(para)}</div>'
    else:
        return ""
    return section("自我评价", body)


def render_clubs_competitions(clubs, comps) -> str:
    out = []
    for c in clubs or []:
        if not isinstance(c, dict):
            continue
        name = c.get("name", "")
        if not name:
            continue
        head = render_entry_head(name, date_range(c.get("start"), c.get("end")))
        role = ""
        if str(c.get("role", "")).strip():
            role = f'<div class="r-role">{esc(c["role"])}</div>'
        desc = ""
        if str(c.get("desc", "")).strip():
            desc = f'<div class="r-detail">{esc(c["desc"])}</div>'
        bullets = render_bullets(c)
        out.append(f'<div class="r-entry">{head}{role}{desc}{bullets}</div>')

    for c in comps or []:
        if not isinstance(c, dict):
            continue
        name = c.get("name", "")
        if not name:
            continue
        head = render_entry_head(name, esc(c.get("date", "")))
        desc = ""
        if str(c.get("desc", "")).strip():
            desc = f'<div class="r-detail">{esc(c["desc"])}</div>'
        bullets = render_bullets(c)
        out.append(f'<div class="r-entry">{head}{desc}{bullets}</div>')

    if not out:
        return ""
    return section("社团与竞赛经历", "\n".join(out))


SKILL_LABELS = {
    "software": "专业软件",
    "languages": "编程语言",
    "hardware": "硬件平台",
    "languages_spoken": "语言",
    "eda_tools": "EDA 工具",
    "professional": "专业能力",
    "ai_tools": "AI 工具",
    "tools": "工具",
    "frameworks": "框架",
    "certificates": "证书",
    "clinical": "临床技能",
    "marketing": "市场与推广",
    "sales": "销售能力",
}


def _humanize_label(key: str) -> str:
    return key.replace("_", " ").capitalize()


def render_skills(sk) -> str:
    if not sk or not isinstance(sk, dict):
        return ""
    out = []
    for key, val in sk.items():  # 保留 YAML 中的书写顺序
        v = str(val).strip() if val else ""
        if not v:
            continue
        label = SKILL_LABELS.get(key) or _humanize_label(key)
        out.append(f'<div class="r-skill-row"><span class="label">{esc(label)}：</span>{esc(v)}</div>')
    if not out:
        return ""
    return section("技能储备", "\n".join(out))


def render_social(sp) -> str:
    if not sp:
        return ""
    org = str(sp.get("org", "")).strip()
    desc = str(sp.get("desc", "")).strip()
    if not (org or desc):
        return ""
    body = ""
    if org:
        body += f'<div class="r-title">{esc(org)}</div>'
    if desc:
        body += f'<div class="r-detail" style="margin-top:2px">{esc(desc)}</div>'
    return section("社会实践", body)


# ============================================================
# LaTeX (tex) 引擎 —— 与上面 HTML 渲染器一一对应
# ------------------------------------------------------------
# 由 --engine tex 调用，模板 templates/classic_single.tex（njq 风格）。
# 中文走 ctex / xelatex；tex_escape 处理数据里的特殊字符。
# ============================================================

# LaTeX 文本模式特殊字符单遍转义（str.translate 不会对已插入的反斜杠二次转义）
_LATEX_ESC = {
    ord("\\"): r"\textbackslash{}",
    ord("&"): r"\&",
    ord("%"): r"\%",
    ord("$"): r"\$",
    ord("#"): r"\#",
    ord("_"): r"\_",
    ord("{"): r"\{",
    ord("}"): r"\}",
    ord("~"): r"\textasciitilde{}",
    ord("^"): r"\textasciicircum{}",
}


def tex_escape(s) -> str:
    """LaTeX 文本模式转义；None/数字安全处理。"""
    if s is None:
        return ""
    return str(s).translate(_LATEX_ESC)


def tex_date_range(start, end) -> str:
    s = tex_escape(start)
    e = tex_escape(end)
    if s and e:
        return f"{s} -- {e}"
    return s or e


def tex_section(title: str, body: str) -> str:
    if not body.strip():
        return ""
    return f"\\section{{{title}}}\n{body}\n"


def _tex_resumeitem(bullets) -> str:
    """bullets 列表 → resumeitem 环境；非列表或空则空串。"""
    if not isinstance(bullets, list):
        return ""
    items = [tex_escape(str(b).strip()) for b in bullets if str(b).strip()]
    if not items:
        return ""
    body = "\n".join(f"    \\item {it}" for it in items)
    return "\\begin{resumeitem}\n" + body + "\n\\end{resumeitem}"


def _tex_entry(name: str, date: str, role: str = "", desc: str = "", bullets_env: str = "") -> str:
    """通用经历条目（njq 风格）：\\textbf 标题+日期 / \\textit 职位 / 描述 / 要点列表。

    单行之间用 \\\\ 断行，最后一行不带 \\\\；要点列表作为独立块追加，其前无 \\\\。
    """
    parts = [f"\\textbf{{{tex_escape(name)}}} \\hfill {date}"]
    if role:
        parts.append(f"\\textit{{{tex_escape(role)}}}")
    if desc:
        parts.append(tex_escape(desc))
    if bullets_env:
        head = " \\\\\n".join(parts)
        if len(parts) == 1:
            head += " \\\\"  # 只有标题行时，列表前仍需一个断行
        return head + "\n" + bullets_env
    return " \\\\\n".join(parts)


def render_header_tex(p: dict) -> str:
    if not p:
        return ""
    name = tex_escape(p.get("name_cn", ""))
    if not name:
        return ""
    name_cell = f"{{\\LARGE \\textbf{{{name}}}}}"
    en = str(p.get("name_en", "")).strip()
    if en:
        name_cell += f" {{\\large \\textbf{{{tex_escape(en)}}}}}"

    rows = [(name_cell, "\\makebox[2.5cm]{}")]
    contact_bits = []
    if p.get("phone"):
        contact_bits.append(f"电话: {tex_escape(p['phone'])}")
    if p.get("email"):
        contact_bits.append(f"邮箱: {tex_escape(p['email'])}")
    if contact_bits:
        rows.append((f"\\small {' \\quad '.join(contact_bits)}", ""))
    if str(p.get("extra", "")).strip():
        rows.append((f"\\small {tex_escape(p['extra'])}", ""))
    if p.get("address"):
        rows.append((f"\\small 地址: {tex_escape(p['address'])}", ""))
    if p.get("target"):
        rows.append((f"\\small \\textbf{{求职意向：{tex_escape(p['target'])}}}", ""))

    out = ["\\noindent", "\\begin{tabular*}{\\textwidth}{@{}l@{\\extracolsep{\\fill}}r@{}}"]
    for i, (left, right) in enumerate(rows):
        sep = " \\\\[1pt]" if i < len(rows) - 1 else ""
        out.append(f"    {left} & {right}{sep}")
    out.append("\\end{tabular*}")
    block = "\n".join(out)

    photo = str(p.get("_photo_path", "")).strip()
    if photo:
        yshift = str(p.get("_photo_yshift", "-1.3cm")).strip() or "-1.3cm"
        height = str(p.get("_photo_height", "3.3cm")).strip() or "3.3cm"
        block += (
            "\n\\begin{tikzpicture}[remember picture, overlay]\n"
            f"  \\node[anchor=north east, xshift=-1.2cm, yshift={yshift}]"
            " at (current page.north east)\n"
            f"    {{\\includegraphics[height={height}]{{{photo}}}}};\n"
            "\\end{tikzpicture}"
        )
    return block + "\n"


def render_education_tex(items) -> str:
    if not items:
        return ""
    out = []
    for e in items:
        if not isinstance(e, dict) or e.get("optional"):
            continue
        school = e.get("school", "")
        if not school:
            continue
        parts = [f"\\textbf{{{tex_escape(school)}}} \\hfill {tex_date_range(e.get('start'), e.get('end'))}"]
        if e.get("major"):
            parts.append(tex_escape(e["major"]))
        block = " \\\\\n".join(parts)
        bits = []
        if e.get("gpa"):
            bits.append(tex_escape(e["gpa"]))
        if e.get("courses"):
            bits.append(tex_escape(e["courses"]))
        if bits:
            block += " \\\\\n\\small " + " \\quad ".join(bits)
        out.append(block)
    if not out:
        return ""
    return tex_section("教育背景", "\n\n".join(out))


def render_work_tex(items) -> str:
    if not items:
        return ""
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        name = it.get("name", "")
        if not name:
            continue
        out.append(_tex_entry(
            name, tex_date_range(it.get("start"), it.get("end")),
            role=str(it.get("role", "")).strip(),
            desc=str(it.get("desc", "")).strip(),
            bullets_env=_tex_resumeitem(it.get("bullets")),
        ))
    if not out:
        return ""
    return tex_section("工作经历", "\n\n".join(out))


def render_projects_tex(items) -> str:
    if not items:
        return ""
    out = []
    for p in items:
        if not isinstance(p, dict):
            continue
        name = p.get("name", "")
        if not name:
            continue
        desc = str(p.get("desc", "")).strip()
        tech = str(p.get("tech", "")).strip()
        details = str(p.get("details", "")).strip()
        text = desc
        if tech:
            text = f"{text}：{tech}" if text else tech
        if details:
            text = f"{text}。{details}" if text else details
        out.append(_tex_entry(
            name, tex_date_range(p.get("start"), p.get("end")),
            role=str(p.get("role", "")).strip(),
            desc=text,
            bullets_env=_tex_resumeitem(p.get("bullets")),
        ))
    if not out:
        return ""
    return tex_section("核心科研与项目经历", "\n\n".join(out))


def render_lab_tex(items) -> str:
    if not items:
        return ""
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        name = it.get("name", "")
        if not name:
            continue
        out.append(_tex_entry(
            name, tex_date_range(it.get("start"), it.get("end")),
            desc=str(it.get("desc", "")).strip(),
            bullets_env=_tex_resumeitem(it.get("bullets")),
        ))
    if not out:
        return ""
    return tex_section("实验室经历", "\n\n".join(out))


def render_clubs_competitions_tex(clubs, comps) -> str:
    out = []
    for c in clubs or []:
        if not isinstance(c, dict):
            continue
        name = c.get("name", "")
        if not name:
            continue
        out.append(_tex_entry(
            name, tex_date_range(c.get("start"), c.get("end")),
            role=str(c.get("role", "")).strip(),
            desc=str(c.get("desc", "")).strip(),
            bullets_env=_tex_resumeitem(c.get("bullets")),
        ))
    for c in comps or []:
        if not isinstance(c, dict):
            continue
        name = c.get("name", "")
        if not name:
            continue
        out.append(_tex_entry(
            name, tex_escape(c.get("date", "")),
            desc=str(c.get("desc", "")).strip(),
            bullets_env=_tex_resumeitem(c.get("bullets")),
        ))
    if not out:
        return ""
    return tex_section("社团与竞赛经历", "\n\n".join(out))


def render_self_tex(se) -> str:
    """自我评价：字符串=整段 / 列表=resumeitem 要点 / {points:[...]}=要点。"""
    if se is None:
        return ""
    points = None
    para = ""
    if isinstance(se, str):
        para = se.strip()
    elif isinstance(se, list):
        points = [str(x).strip() for x in se if str(x).strip()]
    elif isinstance(se, dict):
        raw = se.get("points")
        if isinstance(raw, list):
            points = [str(x).strip() for x in raw if str(x).strip()]
        if not points:
            para = str(se.get("desc", "")).strip()
    else:
        return ""
    if points:
        body = _tex_resumeitem(points)
    elif para:
        body = tex_escape(para)
    else:
        return ""
    return tex_section("自我评价", body)


def render_skills_tex(sk) -> str:
    if not sk or not isinstance(sk, dict):
        return ""
    rows = []
    for key, val in sk.items():  # 保留 YAML 中的书写顺序
        v = str(val).strip() if val else ""
        if not v:
            continue
        label = SKILL_LABELS.get(key) or _humanize_label(key)
        rows.append(f"\\textbf{{{tex_escape(label)}}}：{tex_escape(v)}")
    if not rows:
        return ""
    return tex_section("技能储备", " \\\\\n".join(rows))


def render_social_tex(sp) -> str:
    if not sp:
        return ""
    org = str(sp.get("org", "")).strip()
    desc = str(sp.get("desc", "")).strip()
    if not (org or desc):
        return ""
    lines = []
    if org:
        lines.append(f"\\textbf{{{tex_escape(org)}}}")
    if desc:
        lines.append(tex_escape(desc))
    return tex_section("社会实践", " \\\\\n".join(lines))


# ---------- 数据加载 ----------
def load_data(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(text)
    # yaml/yml 或其它：优先 yaml，无 PyYAML 则尝试 json
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except ImportError:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            sys.exit(
                "无法解析数据文件：未安装 PyYAML 且内容不是合法 JSON。\n"
                "解决：pip install pyyaml，或把数据另存为 .json。"
            )


# ---------- 主流程 ----------
def parse_args():
    ap = argparse.ArgumentParser(description="简历数据(YAML/JSON) → HTML + PDF（默认无 LaTeX）或 TeX + PDF（--engine tex）。")
    ap.add_argument("data", help="数据文件路径 (.yaml/.yml/.json)")
    ap.add_argument("--engine", choices=["html", "tex"], default="html",
                    help="排版引擎：html(默认, Chrome 无头打印) | tex(本机 xelatex 编译)")
    ap.add_argument("--template", default="classic_single", help="模板名(templates 目录下)或绝对路径")
    ap.add_argument("--out", default=None, help="输出路径（默认 resume.html / resume.tex）")
    ap.add_argument("--pdf", default=None, help="输出 PDF 路径（默认与主文件同名 .pdf）")
    ap.add_argument("--no-pdf", action="store_true", help="只生成 HTML/TeX，不自动出 PDF")
    ap.add_argument("--photo", default=None, help="证件照图片路径（直接使用，不再提取）")
    ap.add_argument("--photo-from", default=None,
                    help="从该源文件(.pdf/.jpg/.png)自动识别并裁剪证件照（纯算法）")
    return ap.parse_args()


# ---------- 证件照 ----------
def _photo_data_uri(path: Path) -> str:
    """把图片文件编码为 base64 data-URI（HTML 自包含，Chrome 打印可渲染）。"""
    import base64
    ext = path.suffix.lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png"}.get(ext, "png")
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{b64}"


def _resolve_photo(args, data: dict, out_path: Path) -> None:
    """解析证件照并写入 data['personal']['_photo_data_uri']。

    优先级：--photo（直接用图）> --photo-from（自动提取）> personal.photo。
    提取/复制后的 PNG 落在 HTML 同目录的 <stem>_photo.png（供 .tex \\includegraphics 用）。
    无 --photo* 且无 personal.photo 时，什么都不做（特性 opt-in）。
    """
    explicit = args.photo or (data.get("personal", {}) or {}).get("photo")
    src_from = args.photo_from

    if not explicit and not src_from:
        return

    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    photo_png = out_dir / (out_path.stem + "_photo.png")

    ok = False
    if src_from:
        try:
            from extract_photo import extract_photo as _extract
            p = _extract(src_from, photo_png)
            ok = bool(p and Path(p).exists())
        except Exception as e:
            print(f"⚠️ 证件照自动提取失败：{e}", file=sys.stderr)
    elif explicit:
        explicit = Path(explicit)
        if not explicit.exists():
            print(f"⚠️ 证件照文件不存在：{explicit}", file=sys.stderr)
        else:
            try:
                photo_png.write_bytes(explicit.read_bytes())  # 复制并统一命名
                ok = True
            except Exception as e:
                print(f"⚠️ 证件照复制失败：{e}", file=sys.stderr)

    if ok and photo_png.exists():
        pdata = data.setdefault("personal", {})
        pdata["_photo_data_uri"] = _photo_data_uri(photo_png)
        pdata["_photo_path"] = photo_png.name  # 供 tex 引擎 \includegraphics（与 .tex 同目录）
        print(f"证件照已嵌入: {photo_png.resolve()}")
    else:
        print("⚠️ 未嵌入证件照（继续生成无照片版本）", file=sys.stderr)


def resolve_template(name: str, engine: str = "html") -> Path:
    p = Path(name)
    if p.is_absolute() or p.exists():
        return p
    suffix = ".tex" if engine == "tex" else ".html"
    candidate = TEMPLATES_DIR / (name if name.endswith(suffix) else f"{name}{suffix}")
    if candidate.exists():
        return candidate
    sys.exit(f"找不到模板: {name}（在 {TEMPLATES_DIR} 下也没找到）")


def render_pdf_for(html_path: Path, pdf_arg) -> None:
    """best-effort 自动 HTML→PDF。失败不影响已生成的 HTML。"""
    pdf_path = Path(pdf_arg) if pdf_arg else html_path.with_suffix(".pdf")
    try:
        from render_pdf import count_pages, detect_browser, print_to_pdf
    except Exception as e:  # 模块加载失败
        print(f"⚠️ 无法加载渲染模块 render_pdf：{e}", file=sys.stderr)
        return
    try:
        browser = detect_browser(None)
        print_to_pdf(browser, html_path, pdf_path)
        pages = count_pages(pdf_path)
        print(f"PDF 已生成: {pdf_path.resolve()}")
        if pages is not None:
            print(f"页数: {pages}")
    except FileNotFoundError as e:
        print(f"⚠️ 未生成 PDF（找不到 Chrome/Edge）：{e}", file=sys.stderr)
        print("   可在浏览器打开 HTML 后「打印 → 另存为 PDF」。", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ PDF 生成失败：{e}", file=sys.stderr)
        print("   HTML 已生成，可手动打印为 PDF。", file=sys.stderr)


def render_pdf_tex(tex_path: Path, pdf_arg) -> None:
    """TeX → PDF：xelatex 跑两遍 + 自动清理中间文件。

    必须用 xelatex（ctex 中文 / tikz）；cwd 设为 .tex 所在目录，使
    \\includegraphics 相对路径与 aux 文件都落在该目录。
    """
    import subprocess
    out_dir = tex_path.parent
    pdf_path = Path(pdf_arg) if pdf_arg else tex_path.with_suffix(".pdf")

    cmd = ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name]
    try:
        for i in (1, 2):
            r = subprocess.run(cmd, cwd=str(out_dir), capture_output=True, text=True)
            if r.returncode != 0:
                log = out_dir / (tex_path.stem + ".log")
                print(f"⚠️ xelatex 第 {i} 遍失败 (rc={r.returncode})。", file=sys.stderr)
                if log.exists():
                    tail = log.read_text(encoding="utf-8", errors="ignore").splitlines()
                    print("--- .log 末尾 30 行 ---", file=sys.stderr)
                    print("\n".join(tail[-30:]), file=sys.stderr)
                else:
                    print(r.stdout[-2000:], file=sys.stderr)
                print("   .tex 已生成，可手动排查后重跑 xelatex。", file=sys.stderr)
                return
    except FileNotFoundError:
        print("⚠️ 找不到 xelatex，请安装 MiKTeX 或 TeX Live 并加入 PATH。", file=sys.stderr)
        print("   .tex 已生成，可在支持 xelatex 的环境编译。", file=sys.stderr)
        return

    produced = out_dir / (tex_path.stem + ".pdf")
    if produced != pdf_path and produced.exists():
        produced.replace(pdf_path)

    print(f"PDF 已生成: {pdf_path.resolve()}")
    try:
        import fitz  # type: ignore
        d = fitz.open(str(pdf_path))
        print(f"页数: {d.page_count}")
        d.close()
    except Exception:
        pass

    # 清理中间文件（保留 .tex / .pdf）
    for ext in (".aux", ".log", ".out", ".toc", ".synctex.gz",
                ".fls", ".fdb_latexmk", ".xdv", ".bbl", ".blg"):
        f = out_dir / (tex_path.stem + ext)
        if f.exists():
            try:
                f.unlink()
            except OSError:
                pass


def main() -> int:
    args = parse_args()
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"数据文件不存在: {data_path}", file=sys.stderr)
        return 1

    data = load_data(data_path)
    engine = args.engine

    out_path = Path(args.out) if args.out else Path(
        "resume.tex" if engine == "tex" else "resume.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 证件照（opt-in）：--photo / --photo-from / personal.photo
    # 同时写 _photo_data_uri(HTML base64) 与 _photo_path(.tex \includegraphics)
    _resolve_photo(args, data, out_path)

    if engine == "tex":
        tex = resolve_template(args.template, engine).read_text(encoding="utf-8")
        # 可选：YAML 的 tex.linespread 覆盖模板默认 \linespread{1.8}
        # （njq 用 1.8 撑满短简历；内容多时调小以避免溢出第二页）
        tex_opts = data.get("tex") or {}
        if isinstance(tex_opts, dict):
            ls = tex_opts.get("linespread")
            if ls:
                tex = tex.replace("\\linespread{1.8}", f"\\linespread{{{ls}}}")
            # 照片位置/尺寸透传给 render_header_tex（仅在有照片时生效）
            pdata = data.setdefault("personal", {})
            for k_src, k_dst in (("photo_yshift", "_photo_yshift"),
                                 ("photo_height", "_photo_height")):
                v = tex_opts.get(k_src)
                if v is not None:
                    pdata[k_dst] = v
        replacements = {
            "%@@HEADER@@": render_header_tex(data.get("personal", {})),
            "%@@EDUCATION@@": render_education_tex(data.get("education")),
            "%@@WORK@@": render_work_tex(data.get("work_experience")),
            "%@@PROJECTS@@": render_projects_tex(data.get("projects")),
            "%@@LAB@@": render_lab_tex(data.get("lab_experience")),
            "%@@CLUBS_COMPETITIONS@@": render_clubs_competitions_tex(
                data.get("clubs"), data.get("competitions")
            ),
            "%@@SELF@@": render_self_tex(data.get("self_evaluation")),
            "%@@SKILLS@@": render_skills_tex(data.get("skills")),
            "%@@SOCIAL@@": render_social_tex(data.get("social_practice")),
        }
        for token, value in replacements.items():
            tex = tex.replace(token, value)
        out_path.write_text(tex, encoding="utf-8")
        print(f"TeX 已生成: {out_path.resolve()}")
        print(f"模板: {args.template} (engine=tex)")
        if not args.no_pdf:
            render_pdf_tex(out_path, args.pdf)
        return 0

    # ---- 默认 HTML 引擎（无 LaTeX）----
    html = resolve_template(args.template, engine).read_text(encoding="utf-8")

    replacements = {
        "<!--HEADER-->": render_header(data.get("personal", {})),
        "<!--EDUCATION-->": render_education(data.get("education")),
        "<!--WORK-->": render_work(data.get("work_experience")),
        "<!--PROJECTS-->": render_projects(data.get("projects")),
        "<!--LAB-->": render_lab(data.get("lab_experience")),
        "<!--CLUBS_COMPETITIONS-->": render_clubs_competitions(
            data.get("clubs"), data.get("competitions")
        ),
        "<!--SELF-->": render_self(data.get("self_evaluation")),
        "<!--SKILLS-->": render_skills(data.get("skills")),
        "<!--SOCIAL-->": render_social(data.get("social_practice")),
    }
    for token, value in replacements.items():
        html = html.replace(token, value)

    out_path.write_text(html, encoding="utf-8")
    print(f"HTML 已生成: {out_path.resolve()}")
    print(f"模板: {args.template}")

    # 一条命令自动出 PDF（开箱即用）；--no-pdf 可跳过
    if not args.no_pdf:
        render_pdf_for(out_path, args.pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
