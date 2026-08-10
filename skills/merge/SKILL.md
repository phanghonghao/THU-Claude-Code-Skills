---
name: merge
description: Merge multiple videos into a single grid video. Supports custom NxM layouts, labels, loop-to-longest duration, and streaming mode for large grids. Use when user mentions "merge videos", "合并视频", "拼视频", "视频对比", "video grid", "视频拼接", "compare videos", or "side by side video".
---

# Merge Videos

Merge multiple MP4 videos into a single grid-layout video with optional labels.

## Permanent Script

The merge tool is the permanent CLI script next to this file:

```text
<this skill directory>\merge_videos.py
```

After syncing to Claude with `codex2claude`, use the copied script in Claude's `merge`
skill directory. Do not use hardcoded stale paths such as `.claude-key3`.

**Do not generate temporary merge scripts.** Always call this permanent script directly with `python`.

## Templates

| Template | Layout | Video Count | Description |
|---|---:|---:|---|
| `2x1` | 2 rows, 1 col | 2 | Vertical stack of 2 videos |
| `3x1` | 3 rows, 1 col | 3 | Vertical stack of 3 videos |
| `2x2` | 2 rows, 2 cols | 4 | Square grid, TL TR BL BR |
| `3x2` | 3 rows, 2 cols | 6 | Tall grid, 6 cells |
| `NxM` | N rows, M cols | N*M | Any arbitrary grid, auto-parsed |

Auto-detect template when `-t` is omitted:

- 2 videos -> `2x1`
- 3 videos -> `3x1`
- 4 videos -> `2x2`
- 6 videos -> `3x2`

For any other count, pass `-t`, for example `-t 8x4` for 32 videos.

## Workflow

1. Find video paths from user arguments, globbing a directory when needed.
2. Determine the template from the user request or by auto-detect.
3. Auto-generate labels from filenames unless custom labels or `--no-labels` are requested.
4. Use `--loop-to-longest` when the user wants the longest video to define the full episode and shorter videos to replay.
5. Use `--stream` for large grids or long videos so encoded frames are written incrementally instead of held in memory.
6. Run the permanent script directly:

```powershell
python "<this skill directory>\merge_videos.py" <video_paths> -t <template> --labels <labels...> -o <output>
```

7. Report output path, frame count, duration, resolution, and file size.

## CLI Parameters

```text
python merge_videos.py VIDEO [VIDEO ...] [-t TEMPLATE] [--labels LABEL [LABEL ...]]
                       [-o OUTPUT] [--gap N] [--fps N] [--font-size N] [--no-labels]
                       [--loop-to-longest] [--stream]
                       [--cell-width N] [--cell-height N]
```

| Parameter | Description | Default |
|---|---|---|
| `videos` | Input video file paths | Required |
| `-t`, `--template` | Layout: `2x1`, `3x1`, `2x2`, `3x2`, or custom `NxM` | Auto-detect from count |
| `--labels` | Custom label for each cell | Auto from filenames |
| `-o`, `--output` | Output file path | `<first_video_dir>/merge_<template>.mp4` |
| `--gap` | Pixel gap between cells | `4` |
| `--fps` | Output frame rate | `30` |
| `--font-size` | Label font size | `20` |
| `--no-labels` | Skip cell labels | Off |
| `--loop-to-longest` | Use the longest input duration; shorter videos loop from frame 0 | Off |
| `--stream` | Stream encoded output frames; required for large grids/long videos | Off |
| `--cell-width` | Maximum output width per grid cell, preserving aspect ratio | None |
| `--cell-height` | Maximum output height per grid cell, preserving aspect ratio | None |

## Examples

**2x2 grid:**

```powershell
python "<this skill directory>\merge_videos.py" `
  "dir\v1.mp4" "dir\v2.mp4" "dir\v3.mp4" "dir\v4.mp4" `
  -t 2x2 --labels "iter 1700" "iter 3000" "iter 5000" "iter 7000" `
  -o "dir\merge_2x2.mp4"
```

**3x1 vertical:**

```powershell
python "<this skill directory>\merge_videos.py" `
  "dir\v1.mp4" "dir\v2.mp4" "dir\v3.mp4" `
  -t 3x1 --labels "IsaacLab" "MuJoCo Humanoid" "MuJoCo Manual"
```

**Large 8x4 grid, longest video defines duration, shorter videos loop:**

```powershell
python "<this skill directory>\merge_videos.py" <32 videos> `
  -t 8x4 --loop-to-longest --stream --fps 50 `
  --cell-width 320 --cell-height 180 `
  -o "merge_8x4_loop_longest.mp4"
```

## Notes

- The script supports arbitrary `NxM` templates via auto-parsing.
- All videos are resized to the smallest common resolution unless `--cell-width` or `--cell-height` caps the cell size.
- Without `--loop-to-longest`, videos are cropped to the shortest input duration.
- With `--loop-to-longest`, the output frame count equals the longest input frame count and shorter videos repeat.
- For high video counts, always prefer `--stream`.

## Prerequisites

Python packages:

```powershell
pip install opencv-python imageio imageio-ffmpeg av Pillow numpy
```
