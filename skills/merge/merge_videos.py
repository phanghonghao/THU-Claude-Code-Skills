#!/usr/bin/env python3
"""merge_videos.py - Permanent CLI tool for merging videos into grid layouts.

Usage:
    python merge_videos.py v1.mp4 v2.mp4 v3.mp4 v4.mp4 -t 2x2 --labels "A" "B" "C" "D"
    python merge_videos.py v1.mp4 v2.mp4 v3.mp4 -t 3x1
    python merge_videos.py v1.mp4 v2.mp4 v3.mp4 v4.mp4 v5.mp4 v6.mp4 -t 3x2
    python merge_videos.py v1.mp4 v2.mp4 -t 2x1 -o output.mp4 --no-labels
"""
import argparse
import sys
from pathlib import Path

import imageio.v2 as imageio
import imageio.v3 as iio
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

# ── Layout definitions ──
LAYOUTS = {
    "2x1": {"rows": 2, "cols": 1},
    "3x1": {"rows": 3, "cols": 1},
    "2x2": {"rows": 2, "cols": 2},
    "3x2": {"rows": 3, "cols": 2},
}

# Auto-detect template from video count
COUNT_TO_TEMPLATE = {
    2: "2x1",
    3: "3x1",
    4: "2x2",
    6: "3x2",
}


def parse_template(template_str):
    """Parse a template string like '2x2' or '3x1' into (rows, cols).
    Supports both predefined names and arbitrary NxM formats."""
    if template_str in LAYOUTS:
        return LAYOUTS[template_str]["rows"], LAYOUTS[template_str]["cols"]
    # Try parsing arbitrary format like "4x3"
    try:
        parts = template_str.lower().split("x")
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    except (ValueError, AttributeError):
        pass
    return None, None


def _get_font(size=20):
    # Try Chinese-capable fonts first (Windows)
    for name in [
        "C:/Windows/Fonts/msyh.ttc",       # Microsoft YaHei (Chinese)
        "C:/Windows/Fonts/simhei.ttf",      # SimHei (Chinese)
        "C:/Windows/Fonts/simsun.ttc",      # SimSun (Chinese)
    ]:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    # Fallback to Western fonts
    for name in ["Consolas.ttf", "DejaVuSansMono.ttf", "arial.ttf", "LiberationMono-Regular.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def compute_positions(h, w, rows, cols, gap):
    positions = []
    for r in range(rows):
        for c in range(cols):
            y = r * (h + gap)
            x = c * (w + gap)
            positions.append((y, x))
    return positions


def _fit_size(width, height, max_width=None, max_height=None):
    if max_width is None and max_height is None:
        return width, height
    cap_w = max_width if max_width is not None else width
    cap_h = max_height if max_height is not None else height
    scale = min(cap_w / width, cap_h / height, 1.0)
    return max(1, int(round(width * scale))), max(1, int(round(height * scale)))


def _draw_labels(canvas, positions, labels, font):
    img = Image.fromarray(canvas)
    draw = ImageDraw.Draw(img)
    for (y, x), label in zip(positions, labels):
        pos = (x + 6, y + 4)
        bbox = draw.textbbox(pos, label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.rounded_rectangle(
            [pos[0] - 2, pos[1] - 1, pos[0] + tw + 4, pos[1] + th + 2],
            radius=3, fill=(0, 0, 0, 180),
        )
        draw.text(pos, label, font=font, fill=(255, 255, 0))
    return np.array(img)


def _merge_videos_stream(video_paths, template, labels, output, gap, fps, font_size,
                         loop_to_longest, cell_width, cell_height):
    rows, cols = parse_template(template)
    caps = []
    sizes = []
    counts = []
    for p in video_paths:
        cap = cv2.VideoCapture(str(p))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {p}")
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if count <= 0:
            raise RuntimeError(f"Could not determine frame count: {p}")
        sizes.append((height, width))
        counts.append(count)
        caps.append(cap)
        print(f"  Opened {p.parent.name}/{p.name} ... {count} frames ({width}x{height})")

    target_w = min(s[1] for s in sizes)
    target_h = min(s[0] for s in sizes)
    target_w, target_h = _fit_size(target_w, target_h, cell_width, cell_height)
    out_n = max(counts) if loop_to_longest else min(counts)
    out_h = rows * target_h + (rows - 1) * gap
    out_w = cols * target_w + (cols - 1) * gap
    positions = compute_positions(target_h, target_w, rows, cols, gap)
    font = _get_font(font_size) if labels else None
    mode = "loop-to-longest" if loop_to_longest else "crop-to-shortest"
    print(f"  Target cell: {target_w}x{target_h}")
    print(f"  Composing {out_n} frames at {out_w}x{out_h} ({template}, {mode}) ...")

    output.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(str(output), fps=fps, codec="libx264", macro_block_size=1)
    try:
        for i in range(out_n):
            canvas = np.full((out_h, out_w, 3), (60, 60, 60), dtype=np.uint8)
            for j, (y, x) in enumerate(positions):
                ok, frame_bgr = caps[j].read()
                if not ok:
                    if not loop_to_longest:
                        raise RuntimeError(f"Unexpected early EOF: {video_paths[j]}")
                    caps[j].set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ok, frame_bgr = caps[j].read()
                    if not ok:
                        raise RuntimeError(f"Could not loop video: {video_paths[j]}")
                frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                if frame.shape[1] != target_w or frame.shape[0] != target_h:
                    frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
                canvas[y:y + target_h, x:x + target_w] = frame
            if labels:
                canvas = _draw_labels(canvas, positions, labels, font)
            writer.append_data(canvas)
            if (i + 1) % 100 == 0:
                print(f"    {i + 1}/{out_n}")
    finally:
        writer.close()
        for cap in caps:
            cap.release()

    size_mb = output.stat().st_size / 1024 / 1024
    print(f"\nDone: {output} ({out_n} frames, {size_mb:.1f} MB)")


def merge_videos(videos, template, labels=None, output=None, gap=4, fps=30,
                 font_size=20, no_labels=False, loop_to_longest=False,
                 stream=False, cell_width=None, cell_height=None):
    video_paths = [Path(p) for p in videos]

    # Determine template
    if template is None:
        n = len(video_paths)
        if n not in COUNT_TO_TEMPLATE:
            print(f"Error: Cannot auto-detect template for {n} videos. "
                  f"Use -t to specify (e.g. -t 2x2).", file=sys.stderr)
            sys.exit(1)
        template = COUNT_TO_TEMPLATE[n]

    rows, cols = parse_template(template)
    if rows is None:
        print(f"Error: Unknown template '{template}'. Use format like 2x2, 3x1, etc.",
              file=sys.stderr)
        sys.exit(1)

    expected = rows * cols
    if len(video_paths) != expected:
        print(f"Error: Template '{template}' ({rows}x{cols}) needs {expected} videos, "
              f"got {len(video_paths)}.", file=sys.stderr)
        sys.exit(1)

    # Default output path
    if output is None:
        first = video_paths[0].parent
        output = first / f"merge_{template}.mp4"
    else:
        output = Path(output)

    # Auto-generate labels from folder/filenames
    if labels is None and not no_labels:
        labels = []
        for p in video_paths:
            # Use parent folder name if video is named generically (like mujoco_manual.mp4)
            stem = p.stem
            if stem in ("mujoco_manual", "mujoco", "output", "video", "recording"):
                labels.append(p.parent.name)
            else:
                labels.append(stem)

    if stream:
        return _merge_videos_stream(
            video_paths, template, labels, output, gap, fps, font_size,
            loop_to_longest, cell_width, cell_height,
        )

    # Load videos
    all_frames = []
    sizes = []
    for p in video_paths:
        print(f"  Loading {p.parent.name}/{p.name} ...", end=" ", flush=True)
        raw = list(iio.imiter(str(p), plugin="pyav"))
        sizes.append(raw[0].shape[:2])
        all_frames.append(raw)
        print(f"{len(raw)} frames ({raw[0].shape[1]}x{raw[0].shape[0]})")

    # Target resolution: smallest common, optionally capped by caller.
    TARGET_W = min(s[1] for s in sizes)
    TARGET_H = min(s[0] for s in sizes)
    TARGET_W, TARGET_H = _fit_size(TARGET_W, TARGET_H, cell_width, cell_height)
    print(f"  Target: {TARGET_W}x{TARGET_H}")

    # Resize
    resized = []
    for frames in all_frames:
        out = []
        for frame in frames:
            if frame.shape[0] != TARGET_H or frame.shape[1] != TARGET_W:
                img = Image.fromarray(frame).resize((TARGET_W, TARGET_H), Image.LANCZOS)
                frame = np.array(img)
            out.append(frame)
        resized.append(out)

    frame_counts = [len(f) for f in resized]
    out_n = max(frame_counts) if loop_to_longest else min(frame_counts)
    h, w = resized[0][0].shape[:2]

    # Grid dimensions
    out_h = rows * h + (rows - 1) * gap
    out_w = cols * w + (cols - 1) * gap
    positions = compute_positions(h, w, rows, cols, gap)
    font = _get_font(font_size) if labels else None

    mode = "loop-to-longest" if loop_to_longest else "crop-to-shortest"
    print(f"  Composing {out_n} frames at {out_w}x{out_h} ({template}, {mode}) ...")

    output.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(str(output), fps=fps, codec="libx264") if stream else None
    result = [] if not stream else None
    for i in range(out_n):
        canvas = np.full((out_h, out_w, 3), (60, 60, 60), dtype=np.uint8)
        for j, (y, x) in enumerate(positions):
            frames = resized[j]
            frame_idx = i % len(frames) if loop_to_longest else i
            canvas[y:y+h, x:x+w] = frames[frame_idx]

        # Draw labels
        if labels:
            canvas = _draw_labels(canvas, positions, labels, font)

        if writer is not None:
            writer.append_data(canvas)
        else:
            result.append(canvas)

        if (i + 1) % 100 == 0:
            print(f"    {i+1}/{out_n}")

    if writer is not None:
        writer.close()
    else:
        iio.imwrite(str(output), result, plugin="pyav", fps=fps, codec="libx264")
    size_mb = output.stat().st_size / 1024 / 1024
    print(f"\nDone: {output} ({out_n} frames, {size_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description="Merge videos into grid layout")
    parser.add_argument("videos", nargs="+", help="Input video paths")
    parser.add_argument("-t", "--template", default=None,
                        help="Layout template: 2x1, 3x1, 2x2, 3x2, or custom NxM")
    parser.add_argument("--labels", nargs="+", default=None,
                        help="Custom label for each cell")
    parser.add_argument("-o", "--output", default=None,
                        help="Output file path")
    parser.add_argument("--gap", type=int, default=4,
                        help="Pixel gap between cells (default: 4)")
    parser.add_argument("--fps", type=int, default=30,
                        help="Output frame rate (default: 30)")
    parser.add_argument("--font-size", type=int, default=20,
                        help="Label font size (default: 20)")
    parser.add_argument("--no-labels", action="store_true",
                        help="Skip cell labels")
    parser.add_argument("--loop-to-longest", action="store_true",
                        help="Use the longest input duration; shorter videos loop")
    parser.add_argument("--stream", action="store_true",
                        help="Stream encoded frames instead of keeping output in memory")
    parser.add_argument("--cell-width", type=int, default=None,
                        help="Maximum output width per grid cell")
    parser.add_argument("--cell-height", type=int, default=None,
                        help="Maximum output height per grid cell")
    args = parser.parse_args()
    merge_videos(args.videos, args.template, args.labels, args.output,
                 args.gap, args.fps, args.font_size, args.no_labels,
                 args.loop_to_longest, args.stream, args.cell_width, args.cell_height)


if __name__ == "__main__":
    main()
