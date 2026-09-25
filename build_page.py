# /// script
# requires-python = ">=3.9"
# ///
"""Assemble data.js for the transcript player from transcribe.py's output.

Usage:
    python build_page.py TRANSCRIPTS_DIR [--out data.js] [--audio-dir audio]

Before running: open TRANSCRIPTS_DIR/metadata.json and fill in "speaker"
(a name) and "topics" (a list of short tags, e.g. ["childhood", "travel"])
for each recording. Re-run any time you update metadata.json.
"""

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "transcripts_dir", type=Path, help="Folder produced by transcribe.py"
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("data.js"),
        help="Output JS file for the player",
    )
    ap.add_argument(
        "--audio-dir",
        default="audio",
        help="Folder name (relative to index.html) holding the original audio files",
    )
    args = ap.parse_args()

    meta_path = args.transcripts_dir / "metadata.json"
    if not meta_path.exists():
        sys.exit(f"No metadata.json found in {args.transcripts_dir}")
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))

    records = []
    missing_info = []
    for filename, meta in sorted(metadata.items()):
        transcript_name = meta.get("transcript")
        transcript_path = (
            args.transcripts_dir / transcript_name if transcript_name else None
        )
        segments = []
        if transcript_path and transcript_path.exists():
            data = json.loads(transcript_path.read_text(encoding="utf-8"))
            for seg in data.get("segments", []):
                segments.append(
                    {"start": seg["start"], "end": seg["end"], "text": seg["text"]}
                )
        else:
            print(
                f"Warning: no transcript file for {filename}, skipping its transcript."
            )

        speaker = (meta.get("speaker") or "").strip()
        # topics = meta.get("topics") or []
        if not speaker:
            missing_info.append(filename)

        records.append(
            {
                "id": filename,
                "filename": filename,
                "audio": f"{args.audio_dir}/{filename}",
                "speaker": speaker or "Unknown",
                # "topics": topics,
                "duration_sec": meta.get("duration_sec", 0),
                "segments": segments,
            }
        )

    args.out.write_text(
        "window.RECORDINGS = "
        + json.dumps(records, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.out} with {len(records)} recordings.")
    if missing_info:
        print(
            "\nThese recordings still need speaker and/or topics filled in metadata.json:"
        )
        for f in missing_info:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
