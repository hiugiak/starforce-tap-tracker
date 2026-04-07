# starforce-tap-tracker

English | [简体中文](README.zh-CN.md)

A small tool for analyzing MapleStory Star Force enhancement results from recorded videos.

The project currently centers on `tap_tracker.py`, which scans a recording, detects the starting star level and enhancement result for each attempt, and outputs aggregated CSV statistics for success, failure, and destruction rates.

## Features

`tap_tracker.py` samples frames from a video and uses template matching to detect:

- Enhancement results: `success` / `failed` / `destroyed` / `protected`
- Starting star levels: `15` through `23`

Notes:

- `protected` is counted in the `destroyed` bucket
- Final output is grouped by base starforce level
- Progress and per-match logs are written to stderr

## Requirements

- Python 3.10+

Dependencies:

- `numpy`
- `opencv-python`

Install example:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

`tap_tracker.py` requires both a recording path and a resize width:

```bash
python3 tap_tracker.py /path/to/video.mp4 --resize-width 1280
```

### Parameters

- `video`: path to the recorded video
- `--resize-width`: first confirm `Graphics -> Resolution` and `UI -> UI Size` in game, then choose the value from the table below:

| Resolution | UI Size | Value |
| --- | --- | --- |
| `1024x768` | `-` | `1024` |
| `1280x720` or `2560x1440` | `-` | `1280` |
| `1366x768` or `2732x1535` | `-` | `1366` |
| `1920x1080` or `3840x2160` | `default ratio` | `1366` |
| `1920x1080` or `3840x2160` | `ideal ratio` | `1920` |

Full help:

```bash
python3 tap_tracker.py --help
```

## Output Example

Standard output is CSV in the following format:

```csv
base_starforce,success,failed,destroyed,total,success_rate,failed_rate,destroyed_rate
15,120,80,3,203,0.591133,0.394089,0.014778
16,98,72,4,174,0.563218,0.413793,0.022989
```

You can redirect it directly into a file:

```bash
python3 tap_tracker.py /path/to/video.mp4 --resize-width 1280 > result.csv
```

## Notes

For stable results, it is recommended to:

- Confirm `Graphics -> Resolution` and `UI -> UI Size` in game, then choose `--resize-width` from the table above
- Make sure the game window fills the full video width
- Make sure the game image is not cropped or stretched

## Project Structure

```text
.
├── tap_tracker.py
└── templates/
    ├── success.png
    ├── success_mask.png
    ├── failed.png
    ├── failed_mask.png
    ├── destroyed.png
    ├── destroyed_mask.png
    ├── protected.png
    ├── protected_mask.png
    ├── 15star.png
    ├── ...
    └── 23star.png
```

## Template Requirements

Templates are loaded from `templates/` by default.

Required result template filenames:

- `success.png`
- `failed.png`
- `destroyed.png`
- `protected.png`

If a result template uses a mask, the corresponding mask filename should be:

- `success_mask.png`
- `failed_mask.png`
- `destroyed_mask.png`
- `protected_mask.png`

Required star-level template filenames:

- `15star.png` through `23star.png`

## How It Works

- The video is sampled at up to `10 FPS` to avoid processing every frame
- Result detection is performed in the center cell of a 3x3 grid over the frame
- When a result text first appears, the script looks back through recent frames to find the corresponding base starforce level
- Only levels `15` through `23` are included in the final statistics

## Known Limitations

- Only star levels `15` through `23` are supported right now
- Only resize widths `1024`, `1280`, `1366`, and `1920` are supported

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
