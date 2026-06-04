#!/usr/bin/env python3
"""Create a Final Cut Pro XML timeline split at detected scene cuts."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import datetime as dt
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
import xml.etree.ElementTree as ET


VIDEO_EXTS = {".mp4", ".mov", ".m4v"}
FPS = 30


@dataclass
class Shot:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict[str, float]:
        return {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": round(self.duration, 3),
        }


@dataclass
class ClipAsset:
    asset_id: str
    path: Path
    name: str
    duration: float
    shots: list[Shot]
    width: int | None = None
    height: int | None = None
    frame_duration: str | None = None


@dataclass
class InputSelection:
    base_dir: Path
    videos: list[Path]


def seconds_to_fcpx_time(seconds: float, fps: int = FPS) -> str:
    frames = max(0, int(round(seconds * fps)))
    if frames == 0:
        return "0s"
    return f"{frames}/{fps}s"


def file_url(path: Path) -> str:
    # Path.as_uri() yields a correct, percent-encoded file URL across Python
    # versions. Manually concatenating "file://" + pathname2url() breaks on
    # Python 3.14, where pathname2url() returns an empty authority ("///path")
    # and the result becomes "file://///path".
    return path.resolve().as_uri()


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def ffprobe(path: Path) -> dict[str, Any]:
    result = run([
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(path),
    ])
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    duration = video.get("duration") or data.get("format", {}).get("duration") or 0
    return {
        "duration": float(duration),
        "width": int(video.get("width") or 0) or None,
        "height": int(video.get("height") or 0) or None,
        "frame_duration": stream_frame_duration(video),
    }


def stream_frame_duration(stream: dict[str, Any]) -> str | None:
    rate = stream.get("avg_frame_rate") or stream.get("r_frame_rate")
    if not rate or rate == "0/0" or "/" not in rate:
        return None
    num_s, den_s = rate.split("/", 1)
    try:
        num = int(num_s)
        den = int(den_s)
    except ValueError:
        return None
    if num <= 0 or den <= 0:
        return None
    return f"{den}/{num}s"


def detect_scene_cuts(path: Path, threshold: float) -> list[float]:
    expr = f"select='gt(scene,{threshold})',showinfo"
    result = run(["ffmpeg", "-hide_banner", "-i", str(path), "-filter:v", expr, "-an", "-f", "null", "-"])
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg scene detection failed for {path}: {result.stderr.strip()}")
    cuts: list[float] = []
    for match in re.finditer(r"pts_time:([0-9]+(?:\.[0-9]+)?)", result.stderr):
        cuts.append(float(match.group(1)))
    return sorted(set(cuts))


def cuts_to_shots(cuts: list[float], duration: float, min_len: float) -> list[Shot]:
    boundaries = [0.0]
    for cut in cuts:
        if 0 < cut < duration:
            boundaries.append(cut)
    boundaries.append(duration)
    shots = [Shot(boundaries[i], boundaries[i + 1]) for i in range(len(boundaries) - 1)]
    return merge_short_shots(shots, min_len)


def merge_short_shots(shots: list[Shot], min_len: float) -> list[Shot]:
    merged: list[Shot] = []
    pending: Shot | None = None
    for shot in shots:
        if shot.duration <= 0:
            continue
        if pending is not None:
            shot = Shot(pending.start, shot.end)
            pending = None
        if shot.duration < min_len and merged:
            merged[-1] = Shot(merged[-1].start, shot.end)
        elif shot.duration < min_len:
            pending = shot
        else:
            merged.append(shot)
    if pending is not None:
        merged.append(pending)
    if len(merged) > 1 and merged[-1].duration < min_len:
        tail = merged.pop()
        merged[-1] = Shot(merged[-1].start, tail.end)
    return merged


def build_fcpxml(assets: list[ClipAsset], project_name: str, event_name: str) -> str:
    fcpxml = ET.Element("fcpxml", {"version": "1.9"})
    resources = ET.SubElement(fcpxml, "resources")
    ET.SubElement(resources, "format", {
        "id": "r_project",
        "name": "FFVideoFormat1080p30",
        "frameDuration": "1/30s",
        "width": "1080",
        "height": "1920",
        "colorSpace": "1-1-1 (Rec. 709)",
    })

    for asset in assets:
        src_fmt_id = f"fmt_{asset.asset_id}"
        if asset.width and asset.height:
            ET.SubElement(resources, "format", {
                "id": src_fmt_id,
                "frameDuration": asset.frame_duration or "1/30s",
                "width": str(asset.width),
                "height": str(asset.height),
                "colorSpace": "1-1-1 (Rec. 709)",
            })
        # FCPXML 1.6+ dropped the `src` attribute on <asset>; the media path
        # is carried by the child <media-rep> below. Emitting `src` here fails
        # Final Cut Pro DTD validation ("No declaration for attribute src").
        attrs = {
            "id": asset.asset_id,
            "name": asset.name,
            "start": "0s",
            "duration": seconds_to_fcpx_time(asset.duration),
            "hasVideo": "1",
        }
        if asset.width and asset.height:
            attrs["format"] = src_fmt_id
        asset_el = ET.SubElement(resources, "asset", attrs)
        ET.SubElement(asset_el, "media-rep", {"kind": "original-media", "src": file_url(asset.path)})

    library = ET.SubElement(fcpxml, "library")
    event = ET.SubElement(library, "event", {"name": event_name})
    project = ET.SubElement(event, "project", {"name": project_name})
    total_duration = sum(shot.duration for asset in assets for shot in asset.shots)
    sequence = ET.SubElement(project, "sequence", {
        "format": "r_project",
        "duration": seconds_to_fcpx_time(total_duration),
        "tcStart": "0s",
        "tcFormat": "NDF",
        "renderFormat": "FFRenderFormatProRes422",
        "audioLayout": "stereo",
        "audioRate": "48k",
    })
    spine = ET.SubElement(sequence, "spine")

    offset = 0.0
    shot_num = 1
    for asset in assets:
        for shot in asset.shots:
            clip = ET.SubElement(spine, "asset-clip", {
                "name": f"{asset.path.stem} Shot {shot_num:03d}",
                "ref": asset.asset_id,
                "offset": seconds_to_fcpx_time(offset),
                "start": seconds_to_fcpx_time(shot.start),
                "duration": seconds_to_fcpx_time(shot.duration),
                "tcFormat": "NDF",
            })
            ET.SubElement(clip, "metadata").append(ET.Element("md", {
                "key": "com.apple.proapps.studio.scene",
                "value": f"Shot {shot_num:03d}",
            }))
            offset += shot.duration
            shot_num += 1

    ET.indent(fcpxml, space="  ")
    body = ET.tostring(fcpxml, encoding="unicode", short_empty_elements=True)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + body + "\n"


def list_videos(input_dir: Path) -> list[Path]:
    return sorted(p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS)


def resolve_input(input_path: Path) -> InputSelection:
    if input_path.is_file():
        if input_path.suffix.lower() not in VIDEO_EXTS:
            raise ValueError(f"Input file is not a supported video: {input_path}")
        return InputSelection(base_dir=input_path.parent, videos=[input_path])
    if input_path.is_dir():
        return InputSelection(base_dir=input_path, videos=list_videos(input_path))
    raise FileNotFoundError(f"Input does not exist: {input_path}")


def make_previews(asset: ClipAsset, preview_dir: Path) -> None:
    preview_dir.mkdir(parents=True, exist_ok=True)
    for idx, shot in enumerate(asset.shots[1:], start=1):
        cut = shot.start
        before = max(0.0, cut - (1 / FPS))
        after = min(asset.duration, cut + (1 / FPS))
        prefix = f"{asset.path.stem}_cut_{idx:03d}"
        extract_frame(asset.path, before, preview_dir / f"{prefix}_before.jpg")
        extract_frame(asset.path, after, preview_dir / f"{prefix}_after.jpg")


def extract_frame(video: Path, timestamp: float, output: Path) -> None:
    run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{timestamp:.3f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        "-y",
        str(output),
    ])


def analyze_video(path: Path, asset_id: str, threshold: float, min_len: float) -> ClipAsset:
    info = ffprobe(path)
    cuts = detect_scene_cuts(path, threshold)
    shots = cuts_to_shots(cuts, info["duration"], min_len)
    return ClipAsset(
        asset_id=asset_id,
        path=path,
        name=path.name,
        duration=info["duration"],
        width=info["width"],
        height=info["height"],
        frame_duration=info["frame_duration"],
        shots=shots,
    )


def write_report(assets: list[ClipAsset], out_path: Path, threshold: float, min_len: float) -> None:
    payload = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "settings": {
            "threshold": threshold,
            "min_shot_len": min_len,
            "timeline": {
                "resolution": "1080x1920",
                "rate": "30p",
                "rendering": "Apple ProRes 422",
                "color_space": "Rec. 709",
                "audio": "Stereo 48kHz",
                "muted": True,
            },
        },
        "videos": [
            {
                "file": str(asset.path),
                "duration": round(asset.duration, 3),
                "shot_count": len(asset.shots),
                "shots": [shot.to_dict() for shot in asset.shots],
            }
            for asset in assets
        ],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_project_name(input_path: Path) -> str:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H.%M")
    safe = (input_path.stem if input_path.is_file() else input_path.name).strip() or "Shotcut"
    return f"{safe} Shotcut {stamp}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a vertical 1080x1920 30p FCPXML timeline split by scene cuts.")
    parser.add_argument("input", help="Video file or folder containing mp4/mov/m4v videos")
    parser.add_argument("--export", help="Output .fcpxml path. Default: <video-or-folder-parent>/edit/timeline.fcpxml")
    parser.add_argument("--project-name", help="Final Cut Pro project name. Default is generated")
    parser.add_argument("--event-name", default="4-16-26", help="Final Cut Pro event name")
    parser.add_argument("--threshold", type=float, default=0.35, help="Scene detection threshold; lower finds more cuts")
    parser.add_argument("--min-shot-len", type=float, default=0.35, help="Merge shots shorter than this many seconds")
    parser.add_argument("--no-previews", action="store_true", help="Skip before/after cut preview JPGs")
    args = parser.parse_args(argv)

    input_path = Path(args.input).expanduser().resolve()
    try:
        selection = resolve_input(input_path)
    except (FileNotFoundError, ValueError) as error:
        print(error, file=sys.stderr)
        return 2
    videos = selection.videos
    if not videos:
        print(f"No videos found in {input_path} ({', '.join(sorted(VIDEO_EXTS))})", file=sys.stderr)
        return 2

    edit_dir = selection.base_dir / "edit"
    edit_dir.mkdir(exist_ok=True)
    export_path = Path(args.export).expanduser().resolve() if args.export else edit_dir / "timeline.fcpxml"
    assets = []
    for idx, video in enumerate(videos, start=1):
        print(f"Analyzing {video.name}...")
        asset = analyze_video(video, f"a{idx}", args.threshold, args.min_shot_len)
        assets.append(asset)
        if not args.no_previews:
            make_previews(asset, edit_dir / "cut-previews")

    project_name = args.project_name or build_project_name(input_path)
    export_path.write_text(build_fcpxml(assets, project_name, args.event_name), encoding="utf-8")
    write_report(assets, edit_dir / "scene-report.json", args.threshold, args.min_shot_len)
    print(f"Wrote {export_path}")
    print(f"Wrote {edit_dir / 'scene-report.json'}")
    if not args.no_previews:
        print(f"Wrote previews to {edit_dir / 'cut-previews'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
