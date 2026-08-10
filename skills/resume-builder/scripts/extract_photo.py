#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_photo.py —— 从简历 PDF/图片中【纯算法】检测证件照并裁剪输出。

**不使用任何视觉 / agent API。** 全部为本地图像算法。

主算法（颜色分割，用户指定方案）：
    蓝/红/彩色证件照背景在「白底 + 黑字」页面里是显著的色块。
    HSV 取饱和度 + 亮度阈值 → 二值掩膜 → 形态学合并 → 轮廓 →
    过滤「照片状」矩形（位于页面上部、竖向长宽比、最小面积、内部高饱和）→ 裁剪。

回退（同样是纯算法，无 API）：
    (a) 元数据法：矢量 PDF 内嵌的图片块（PyMuPDF 读取其放置 bbox）。
    (b) 边缘密度法：扫描件 / 白底证件照——在页面顶部找纹理最密的竖向矩形。

CLI:
    python extract_photo.py <源.pdf|jpg|png> [--out photo.png] [--dpi 200] [--method auto|color|metadata|edges]

也可被 build_resume.py 直接 import：extract_photo(src, out, ...) -> Path | None
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 过滤阈值（经验值，可按需调整）
SAT_THRESH = 40      # HSV 饱和度下限：>40 视为「有颜色」
VAL_THRESH = 50      # HSV 亮度下限：排除纯黑文字
MIN_SAT_REGION = 30  # 候选矩形内平均饱和度下限
TOP_RATIO = 0.45     # 照片中心 y 必须落在页面上 45%
ASPECT_MAX = 0.95    # 竖向长宽比 w/h 上限（证件照通常 <0.8）
MIN_AREA_RATIO = 0.005  # 候选最小面积占整页比例
MIN_W_RATIO = 0.04   # 候选最小宽度占页宽比例
MIN_H_RATIO = 0.06   # 候选最小高度占页高比例


# ---------- 图像加载 ----------
def _pdf_to_bgr(src: Path, dpi: int):
    """PDF 第 1 页 → BGR ndarray（顺便返回 doc/page 供元数据回退用）。"""
    import fitz  # PyMuPDF
    import numpy as np

    doc = fitz.open(str(src))
    page = doc[0]
    pix = page.get_pixmap(dpi=dpi)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n >= 3:  # RGB(A) → BGR
        bgr = arr[:, :, :3][:, :, ::-1]
    else:  # 灰度 → 三通道
        bgr = np.stack([arr[:, :, 0]] * 3, axis=-1)
    return bgr, doc, page, dpi


def _image_to_bgr(src: Path):
    import cv2
    img = cv2.imread(str(src))
    if img is None:
        raise ValueError(f"无法读取图片：{src}")
    return img


# ---------- 主检测：颜色 / 区域分割（局部前景密度）----------
def detect_by_color(img):
    """返回最佳「照片状」矩形 (x, y, w, h)（像素坐标）或 None。

    思路：证件照是页面上一个【密集的非背景色块】——无论蓝/红底还是浅灰/户外照，
    相对纯白页面都呈现为「局部前景像素密度高」的竖向矩形。文字虽也是前景，但稀疏，
    密度远低于照片块。故用「非页面白前景 + 局部密度阈值」框出整张照片，再按
    上部位置 / 竖向长宽比 / 最小面积筛选。纯算法，不依赖饱和色底。
    """
    import cv2
    import numpy as np

    H, W = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    # 前景 = 偏暗(V 低) 或 有色(S 高)；页面背景近白(V 高、S 低)被排除
    fg = ((v < 225) | (s > 60)).astype(np.float32)
    # 局部前景密度：竖向窗口（照片竖长）。照片块密度高，文字稀疏密度低。
    kw = max(11, int(W * 0.08))
    kh = max(11, int(H * 0.13))
    kx, ky = min(kw, kh), max(kw, kh)  # 保证 kx<=ky（竖向核）
    dens = cv2.boxFilter(fg, ddepth=-1, ksize=(kx, ky))
    photo_mask = (dens > 0.45).astype(np.uint8) * 255
    # 形态学闭合，把照片内部空隙填实成整体
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    photo_mask = cv2.morphologyEx(photo_mask, cv2.MORPH_CLOSE, k)

    contours, _ = cv2.findContours(photo_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    page_area = H * W
    best = None
    best_area = 0
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        cx, cy = x + w / 2, y + h / 2
        area = w * h
        if cy > TOP_RATIO * H:
            continue
        if w == 0 or h == 0 or w / h >= ASPECT_MAX:
            continue
        if area < MIN_AREA_RATIO * page_area:
            continue
        if w < MIN_W_RATIO * W or h < MIN_H_RATIO * H:
            continue
        # 用面积最大的候选（密度阈值已保证是「照片级」密集块）
        if area > best_area:
            best_area = area
            best = (x, y, w, h)
    return best


# ---------- 回退 (a)：PDF 元数据（内嵌图片块的放置 bbox）----------
def detect_by_metadata(doc, page, dpi):
    """在矢量 PDF 里找「右上角、竖向长宽比」的图片块，返回像素 bbox 或 None。"""
    import fitz
    W_pt, H_pt = page.rect.width, page.rect.height
    scale = dpi / 72.0
    best = None
    best_area = 0
    for blk in page.get_text("dict")["blocks"]:
        if blk.get("type") != 1:  # 仅图片块
            continue
        x0, y0, x1, y1 = blk["bbox"]
        w, h = x1 - x0, y1 - y0
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if cx <= W_pt * 0.5 or cy >= H_pt * 0.4:
            continue
        if w <= 0 or h <= 0 or w / h >= ASPECT_MAX:
            continue
        area = w * h
        if area > best_area:
            best_area = area
            best = (int(x0 * scale), int(y0 * scale), int(w * scale), int(h * scale))
    return best


# ---------- 回退 (b)：边缘密度（扫描件 / 白底照片）----------
def detect_by_edges(img):
    """在页面顶部找纹理最密的竖向矩形，返回像素 bbox 或 None。"""
    import cv2
    import numpy as np

    H, W = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150).astype(np.float32)
    # 用接近照片尺寸的核做均值滤波 = 每个窗口的边缘密度
    kx, ky = max(1, int(W * 0.12)), max(1, int(H * 0.16))
    density = cv2.boxFilter(edges, ddepth=-1, ksize=(kx, ky))
    top = density[: int(H * TOP_RATIO) + ky, :]
    if top.size == 0:
        return None
    _, (ymax, xmax) = np.unravel_index(top.argmax(), top.shape)  # type: ignore
    w, h = kx, ky
    x = min(max(int(xmax - w / 2), 0), W - w)
    y = min(max(int(ymax - h / 2), 0), H - h)
    if density[y:y + h, x:x + w].mean() < 8:  # 纹理太弱 → 可能没有照片
        return None
    return (x, y, w, h)


# ---------- 裁剪 + 保存 ----------
def crop_and_save(img, bbox, out_path: Path) -> Path:
    import cv2
    H, W = img.shape[:2]
    x, y, w, h = bbox
    pad = max(2, int(0.02 * min(w, h)))
    x0 = max(0, x - pad); y0 = max(0, y - pad)
    x1 = min(W, x + w + pad); y1 = min(H, y + h + pad)
    crop = img[y0:y1, x0:x1]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), crop)
    return out_path


# ---------- 对外主入口 ----------
def extract_photo(src, out, dpi: int = 200, method: str = "auto"):
    """检测并裁剪证件照到 out。返回输出 Path；未检测到返回 None。"""
    src = Path(src)
    out = Path(out)
    if not src.exists():
        print(f"源文件不存在：{src}", file=sys.stderr)
        return None

    is_pdf = src.suffix.lower() == ".pdf"
    img = None
    doc = page = None
    if is_pdf:
        img, doc, page, dpi = _pdf_to_bgr(src, dpi)
    else:
        img = _image_to_bgr(src)

    try:
        # 检测顺序：矢量 PDF 优先用元数据（精确读到内嵌照片的放置 bbox），
        # 否则用颜色/区域分割（适合图片/扫描件），最后边缘密度兜底。
        steps = []
        if is_pdf and method in ("auto", "metadata"):
            steps.append(("metadata", lambda: detect_by_metadata(doc, page, dpi)))
        if method in ("auto", "color"):
            steps.append(("color", lambda: detect_by_color(img)))
        if method in ("auto", "edges"):
            steps.append(("edges", lambda: detect_by_edges(img)))
        if method not in ("auto", "color", "metadata", "edges"):
            print(f"未知 method：{method}", file=sys.stderr)
            return None

        for name, fn in steps:
            try:
                bbox = fn()
            except Exception as e:
                print(f"  [{name}] 异常：{e}", file=sys.stderr)
                bbox = None
            if bbox:
                crop_and_save(img, bbox, out)
                print(f"已检测到证件照（方法={name}，bbox={bbox}）→ {out}")
                return out
        print("未检测到证件照（颜色/元数据/边缘均无命中）", file=sys.stderr)
        return None
    finally:
        if doc is not None:
            doc.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="纯算法从简历中检测并裁剪证件照（不用视觉 API）。")
    ap.add_argument("src", help="源文件 (.pdf/.jpg/.png)")
    ap.add_argument("--out", default="photo.png", help="输出 PNG 路径")
    ap.add_argument("--dpi", type=int, default=200, help="PDF 渲染 DPI（默认 200）")
    ap.add_argument("--method", default="auto",
                    choices=["auto", "color", "metadata", "edges"],
                    help="检测方法（默认 auto：color→metadata→edges）")
    args = ap.parse_args()
    p = extract_photo(args.src, args.out, dpi=args.dpi, method=args.method)
    return 0 if p else 0  # 未检测到也不报错（opt-in 特性）


if __name__ == "__main__":
    raise SystemExit(main())
