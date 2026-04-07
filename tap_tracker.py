from __future__ import annotations

import argparse
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


RESULT_TEXTS = ("success", "failed", "destroyed", "protected")
LEVELS = tuple(range(15, 24))
RESIZE_WIDTHS = (1366, 1920)
RESULT_TO_BUCKET = {
    "success": "success",
    "failed": "failed",
    "destroyed": "destroyed",
    "protected": "destroyed",
}
DEFAULT_PROGRESS_INTERVAL = 10
TARGET_PROCESS_FPS = 10.0


@dataclass(frozen=True)
class Template:
    name: str
    image: np.ndarray
    mask: np.ndarray | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze MapleStory starforce enhancement results from a recording."
    )
    parser.add_argument("video", type=Path, help="Recording file path")
    parser.add_argument(
        "-r",
        "--resize-width",
        type=int,
        choices=RESIZE_WIDTHS,
        required=True,
        help="Resize frame width before template matching",
    )
    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=Path("templates"),
        help="Directory containing result and starforce templates",
    )
    parser.add_argument(
        "--result-threshold",
        type=float,
        default=0.99,
        help="Template matching threshold for success/failed/destroyed/protected text",
    )
    parser.add_argument(
        "--level-threshold",
        type=float,
        default=0.98,
        help="Template matching threshold for starforce level text",
    )
    parser.add_argument(
        "--progress-interval",
        type=int,
        default=DEFAULT_PROGRESS_INTERVAL,
        help="Print progress every N frames",
    )
    return parser.parse_args()


def load_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Unable to read template: {path}")
    return image


def load_mask(path: Path) -> np.ndarray | None:
    if not path.exists():
        return None
    mask = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise FileNotFoundError(f"Unable to read mask: {path}")
    return mask


def build_template(name: str, image_path: Path, mask_path: Path | None = None) -> Template:
    image = load_image(image_path)
    mask = load_mask(mask_path) if mask_path is not None else None
    if mask is not None and image.ndim == 3 and mask.ndim == 2:
        mask = np.repeat(mask[:, :, np.newaxis], image.shape[2], axis=2)
    return Template(name=name, image=image, mask=mask)


def load_result_templates(templates_dir: Path) -> list[Template]:
    templates: list[Template] = []
    for text in RESULT_TEXTS:
        image_path = templates_dir / f"{text}.png"
        mask_path = templates_dir / f"{text}_mask.png"
        templates.append(build_template(text, image_path, mask_path))
    return templates


def load_level_templates(templates_dir: Path) -> list[Template]:
    templates: list[Template] = []
    for level in LEVELS:
        image_path = templates_dir / f"{level}star.png"
        templates.append(build_template(str(level), image_path))
    return templates


def resize_frame(frame: np.ndarray, target_width: int) -> np.ndarray:
    height, width = frame.shape[:2]
    if width == target_width:
        return frame
    scale = target_width / width
    target_height = max(1, int(round(height * scale)))
    return cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)


def preprocess_frame(frame: np.ndarray, target_width: int) -> np.ndarray:
    return resize_frame(frame, target_width)


def crop_center_grid(frame: np.ndarray) -> np.ndarray:
    height, width = frame.shape[:2]
    top = height // 3
    bottom = (height * 2) // 3
    left = width // 3
    right = (width * 2) // 3
    return frame[top:bottom, left:right]


def match_score(frame: np.ndarray, template: Template) -> float:
    if (
        frame.shape[0] < template.image.shape[0]
        or frame.shape[1] < template.image.shape[1]
    ):
        return -1.0

    if template.mask is not None:
        result = cv2.matchTemplate(
            frame, template.image, cv2.TM_CCORR_NORMED, mask=template.mask
        )
    else:
        result = cv2.matchTemplate(frame, template.image, cv2.TM_CCORR_NORMED)
    return float(result.max())


def detect_best_match(
    frame: np.ndarray, templates: list[Template], threshold: float
) -> tuple[str | None, float]:
    best_name: str | None = None
    best_score = threshold
    for template in templates:
        score = match_score(frame, template)
        if score >= best_score:
            best_name = template.name
            best_score = score
    return best_name, best_score


def find_base_starforce(
    frame_history: deque[tuple[int, np.ndarray]],
    lookback_frames: int,
    level_templates: list[Template],
    level_threshold: float,
) -> int | None:
    searched = 0
    for _, frame in reversed(frame_history):
        if searched >= lookback_frames:
            break
        level_name, _ = detect_best_match(frame, level_templates, level_threshold)
        if level_name is not None:
            return int(level_name)
        searched += 1

    return None


def total_count(counts: dict[int, dict[str, int]]) -> int:
    return sum(sum(bucket.values()) for bucket in counts.values())


def print_progress(
    processed_frames: int, total_frames: int | None, counts: dict[int, dict[str, int]]
) -> None:
    matched_results = total_count(counts)
    if total_frames and total_frames > 0:
        percent = processed_frames / total_frames * 100
        message = (
            f"\rProcessing frames: {processed_frames}/{total_frames} "
            f"({percent:6.2f}%) | matched results: {matched_results}"
        )
    else:
        message = (
            f"\rProcessing frames: {processed_frames} | "
            f"matched results: {matched_results}"
        )
    print(message, end="", file=sys.stderr, flush=True)


def analyze_video(args: argparse.Namespace) -> dict[int, dict[str, int]]:
    result_templates = load_result_templates(args.templates_dir)
    level_templates = load_level_templates(args.templates_dir)

    counts: dict[int, dict[str, int]] = defaultdict(
        lambda: {"success": 0, "failed": 0, "destroyed": 0}
    )

    capture = cv2.VideoCapture(str(args.video))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video: {args.video}")
    raw_total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    total_frames = raw_total_frames if raw_total_frames > 0 else None
    raw_fps = capture.get(cv2.CAP_PROP_FPS)
    process_fps = (
        min(raw_fps, TARGET_PROCESS_FPS) if raw_fps and raw_fps > 0 else TARGET_PROCESS_FPS
    )
    lookback_frames = max(1, int(round(process_fps / 2)))
    frame_history: deque[tuple[int, np.ndarray]] = deque(maxlen=lookback_frames)
    sample_interval = raw_fps / TARGET_PROCESS_FPS if raw_fps and raw_fps > 0 else 1.0
    next_sample_frame = 0.0
    total_processed_frames = (
        max(1, int(np.ceil(total_frames / sample_interval))) if total_frames is not None else None
    )

    previous_result_present = False
    frame_index = -1
    processed_frame_count = 0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            frame_index += 1
            if frame_index + 1 < next_sample_frame:
                continue
            next_sample_frame += sample_interval
            processed_frame_count += 1

            prepared = preprocess_frame(frame, args.resize_width)
            result_region = crop_center_grid(prepared)
            result_name, _ = detect_best_match(
                result_region, result_templates, args.result_threshold
            )
            result_present = result_name is not None

            if result_present and not previous_result_present:
                base_level = find_base_starforce(
                    frame_history,
                    lookback_frames,
                    level_templates,
                    args.level_threshold,
                )
                if base_level in range(15, 24):
                    bucket = RESULT_TO_BUCKET[result_name]
                    counts[base_level][bucket] += 1
                    matched_total = sum(counts[base_level].values())
                    print(
                        (
                            f"\n[match] frame={frame_index} base_starforce={base_level} "
                            f"result={result_name} level_total={matched_total}"
                        ),
                        file=sys.stderr,
                        flush=True,
                    )

            frame_history.append((frame_index, prepared))
            previous_result_present = result_present

            processed_frames = processed_frame_count
            if (
                processed_frames == 1
                or processed_frames % max(1, args.progress_interval) == 0
            ):
                print_progress(processed_frames, total_processed_frames, counts)
    finally:
        capture.release()

    if processed_frame_count > 0:
        print_progress(processed_frame_count, total_processed_frames, counts)
    print(file=sys.stderr)

    return counts


def print_summary(counts: dict[int, dict[str, int]]) -> None:
    print("base_starforce,success,failed,destroyed,total,success_rate,failed_rate,destroyed_rate")
    for level in LEVELS:
        bucket = counts.get(level)
        if bucket is None:
            continue

        success = bucket["success"]
        failed = bucket["failed"]
        destroyed = bucket["destroyed"]
        total = success + failed + destroyed
        if total == 0:
            continue

        print(
            f"{level},{success},{failed},{destroyed},{total},"
            f"{success / total:.6f},{failed / total:.6f},{destroyed / total:.6f}"
        )


def main() -> None:
    args = parse_args()
    counts = analyze_video(args)
    print_summary(counts)


if __name__ == "__main__":
    main()
