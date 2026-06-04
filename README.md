# FCP Shotcut

FCP Shotcut turns a single downloaded video or a folder of videos into a Final Cut Pro XML timeline where each detected shot is already split into its own editable clip.

It is designed for short-form vertical video workflows: manually collect videos, run FCP Shotcut, import the generated XML into Final Cut Pro, then continue editing by hand.

## What It Creates

The generated Final Cut Pro project is fixed to:

- Video: Vertical
- Resolution: 1080x1920
- Rate: 30p
- Rendering: Apple ProRes 422
- Color Space: Standard Rec. 709
- Audio: Stereo 48kHz

FCP Shotcut does not physically cut or transcode your videos. It references the original media files and creates a timeline like:

```text
[Shot 001][Shot 002][Shot 003][Shot 004]...
```

Each shot is a separate clip in Final Cut Pro, so you can delete, move, trim, retime, grade, and add transitions normally.

## Features

- Detects scene/shot changes with ffmpeg.
- Generates `.fcpxml` for Final Cut Pro import.
- Ships as a small macOS app with a custom icon.
- Keeps source files untouched.
- Supports arbitrary file names, including spaces and Chinese characters.
- Creates a `scene-report.json` with detected shot times.
- Optionally creates before/after cut preview images.
- Includes both a macOS GUI app and command-line entrypoints.

## Requirements

- macOS
- Python 3
- ffmpeg and ffprobe

Install ffmpeg with Homebrew:

```bash
brew install ffmpeg
```

## GUI Usage

Download the release DMG, open it, then double-click:

```text
FCP Shotcut.app
```

Choose one video file or a folder containing videos, adjust scene sensitivity if needed, then click **Generate Final Cut Pro XML**.

The output is written to:

```text
<your video file's folder or video folder>/edit/timeline.fcpxml
```

Import it in Final Cut Pro:

```text
File -> Import -> XML
```

## Command Line Usage

From this repo:

```bash
./fcp-shotcut /path/to/videos
```

For one video file:

```bash
./fcp-shotcut /path/to/video.mp4
```

Or from inside a folder of videos:

```bash
/path/to/fcp-shotcut/fcp-shotcut
```

Output:

```text
/path/to/videos/edit/
├── timeline.fcpxml
├── scene-report.json
└── cut-previews/
```

## Tuning

Lower threshold finds more cuts; higher threshold finds fewer:

```bash
./fcp-shotcut /path/to/videos --threshold 0.28
```

Merge very short shots:

```bash
./fcp-shotcut /path/to/videos --min-shot-len 0.5
```

Skip cut preview JPGs:

```bash
./fcp-shotcut /path/to/videos --no-previews
```

## Accuracy Notes

Shot detection is algorithmic, not magic. It works best on hard cuts and obvious visual changes. It can miss or over-detect:

- flash transitions
- dissolves
- fast camera movement
- heavy filters
- zooms or whip pans inside one shot

The goal is to remove most of the mechanical cutting work and leave a clean, editable Final Cut Pro timeline for human finishing.

## Development

Run tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest test_fcp_shotcut.py
```

Build release DMG and zip assets:

```bash
scripts/build_release.sh
```

Regenerate the app icon:

```bash
python3 scripts/make_icon.py
```

## License

MIT
