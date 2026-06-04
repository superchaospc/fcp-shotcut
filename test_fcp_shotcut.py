import json
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fcp_shotcut import (
    ClipAsset,
    Shot,
    build_fcpxml,
    merge_short_shots,
    resolve_input,
    seconds_to_fcpx_time,
)


class FcpShotcutTests(unittest.TestCase):
    def test_seconds_to_fcpx_time_uses_frame_denominator(self):
        self.assertEqual(seconds_to_fcpx_time(0), "0s")
        self.assertEqual(seconds_to_fcpx_time(1.5), "45/30s")
        self.assertEqual(seconds_to_fcpx_time(1 / 30), "1/30s")

    def test_merge_short_shots_drops_tiny_segments(self):
        shots = [Shot(0, 0.2), Shot(0.2, 1.0), Shot(1.0, 2.0)]
        merged = merge_short_shots(shots, min_len=0.35)
        self.assertEqual([(s.start, s.end) for s in merged], [(0, 1.0), (1.0, 2.0)])

    def test_build_fcpxml_uses_vertical_1080_1920_30p_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "随便 取名.mp4"
            media.write_bytes(b"placeholder")
            asset = ClipAsset(
                asset_id="a1",
                path=media,
                name=media.name,
                duration=10,
                shots=[Shot(0, 2.0), Shot(2.0, 5.0)],
            )
            xml_text = build_fcpxml([asset], project_name="Auto Shotcut Test", event_name="4-16-26")

        root = ET.fromstring(xml_text)
        fmt = root.find("./resources/format[@id='r_project']")
        self.assertEqual(fmt.attrib["width"], "1080")
        self.assertEqual(fmt.attrib["height"], "1920")
        self.assertEqual(fmt.attrib["frameDuration"], "1/30s")
        self.assertIn("Rec. 709", fmt.attrib["colorSpace"])

        sequence = root.find(".//sequence")
        self.assertEqual(sequence.attrib["format"], "r_project")
        self.assertEqual(sequence.attrib["renderFormat"], "FFRenderFormatProRes422")
        self.assertEqual(sequence.attrib["audioLayout"], "stereo")
        self.assertEqual(sequence.attrib["audioRate"], "48k")

        clips = root.findall(".//spine/asset-clip")
        self.assertEqual(len(clips), 2)
        self.assertEqual(clips[0].attrib["offset"], "0s")
        self.assertEqual(clips[0].attrib["start"], "0s")
        self.assertEqual(clips[0].attrib["duration"], "60/30s")
        self.assertEqual(clips[1].attrib["offset"], "60/30s")
        self.assertEqual(clips[1].attrib["start"], "60/30s")

        asset_el = root.find("./resources/asset[@id='a1']")
        self.assertEqual(asset_el.attrib["hasVideo"], "1")
        self.assertNotIn("hasAudio", asset_el.attrib)

    def test_report_shape_is_json_serializable(self):
        shot = Shot(0, 1.25)
        payload = {"shots": [shot.to_dict()]}
        self.assertEqual(json.loads(json.dumps(payload))["shots"][0]["duration"], 1.25)

    def test_resolve_input_accepts_single_video_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "随便取名.mov"
            media.write_bytes(b"placeholder")
            selection = resolve_input(media)

        self.assertEqual(selection.base_dir, media.parent)
        self.assertEqual(selection.videos, [media])

    def test_resolve_input_accepts_video_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            first = folder / "a.mp4"
            second = folder / "b.mov"
            ignored = folder / "notes.txt"
            first.write_bytes(b"placeholder")
            second.write_bytes(b"placeholder")
            ignored.write_text("ignore me", encoding="utf-8")
            selection = resolve_input(folder)

        self.assertEqual(selection.base_dir, folder)
        self.assertEqual(selection.videos, [first, second])


if __name__ == "__main__":
    unittest.main()
