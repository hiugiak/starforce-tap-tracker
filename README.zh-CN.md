# starforce-tap-tracker

[English](README.md) | 简体中文

用于统计《冒险岛》星之力强化结果的小工具。

项目当前主要提供 `tap_tracker.py`，用于分析录屏，识别每次强化的起始星数和结果，统计强化成功率、失败率和毁坏率，并输出汇总 CSV。

## 功能说明

`tap_tracker.py` 会对视频逐帧采样，结合模板匹配识别：

- 强化结果：`success` / `failed` / `destroyed` / `protected`
- 起始星数：`15` 到 `23`

说明：

- `protected` 会被归类到 `destroyed` 桶中统计
- 最终输出为按起始星数聚合的 CSV
- 进度和逐次匹配日志会输出到标准错误

## 环境要求

- Python 3.10 及以上

依赖包：

- `numpy`
- `opencv-python`

安装示例：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 使用方式

`tap_tracker.py` 必须显式指定录屏文件和缩放宽度：

```bash
python3 tap_tracker.py /path/to/video.mp4 --resize-width 1280
```

### 参数

- `video`：录屏文件路径
- `--resize-width`：先在游戏内确认 `Graphics -> Resolution` 和 `UI -> UI Size`，再参考下表选择对应的值：

| Resolution | UI Size | Value |
| --- | --- | --- |
| `1024x768` | `-` | `1024` |
| `1280x720` 或 `2560x1440` | `-` | `1280` |
| `1366x768` 或 `2732x1535` | `-` | `1366` |
| `1920x1080` 或 `3840x2160` | `default ratio` | `1366` |
| `1920x1080` 或 `3840x2160` | `ideal ratio` | `1920` |

查看完整帮助：

```bash
python3 tap_tracker.py --help
```

## 输出示例

标准输出为 CSV，格式如下：

```csv
base_starforce,success,failed,destroyed,total,success_rate,failed_rate,destroyed_rate
15,120,80,3,203,0.591133,0.394089,0.014778
16,98,72,4,174,0.563218,0.413793,0.022989
```

你可以直接重定向到文件：

```bash
python3 tap_tracker.py /path/to/video.mp4 --resize-width 1280 > result.csv
```

## 注意事项

为了保证统计结果稳定，建议：

- 先确认游戏内 `Graphics -> Resolution` 和 `UI -> UI Size` 设置，并按上表选择 `--resize-width`
- 保证游戏窗口宽度充满视频
- 保证游戏画面没有被剪切，游戏画面比例没有被压缩

## 项目结构

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

## 模板要求

默认会从 `templates/` 目录读取模板。

强化结果模板文件名必须是：

- `success.png`
- `failed.png`
- `destroyed.png`
- `protected.png`

如果某个强化结果模板需要 mask，对应文件名应为：

- `success_mask.png`
- `failed_mask.png`
- `destroyed_mask.png`
- `protected_mask.png`

星数模板文件名必须是：

- `15star.png` 到 `23star.png`

## 统计逻辑简述

- 视频会按最多 `10 FPS` 进行采样，避免逐帧全量处理
- 结果识别区域为画面中心九宫格中的中间区域
- 当检测到结果文字首次出现时，脚本会回看前一小段帧历史，寻找对应的起始星数
- 只有识别到 `15` 到 `23` 星时才会计入统计

## 已知限制

- 当前仅支持 `15` 到 `23` 星
- 当前仅支持 `1024`、`1280`、`1366`、`1920` 四种分析宽度

## 许可协议

本项目基于 MIT License 开源，详见 [LICENSE](LICENSE)。
