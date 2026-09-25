# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["faster-whisper"]
# ///
"""Transcribe a folder of audio files into one JSON per file, with word timestamps.

Usage:
    uv run transcribe.py RECORDINGS_DIR
    uv run transcribe.py RECORDINGS_DIR --model medium --prompt "Names: Ana, Beto, Xiomara"

Outputs (in --out, default ./transcripts):
    <audio filename>.json   segments + word-level timestamps for that recording
    metadata.json           one entry per recording; fill in "speaker" and "topics" by hand.
                            Re-running never overwrites what you've filled in.

Already-transcribed files are skipped, so it's safe to stop and resume.
No system ffmpeg needed; faster-whisper decodes audio with its bundled PyAV.
"""
import argparse
import json
import sys
from pathlib import Path

from faster_whisper import WhisperModel

AUDIO_EXTS = {
    ".mp3", ".m4a", ".wav", ".ogg", ".opus", ".aac", ".flac",
    ".amr", ".wma", ".mp4", ".webm", ".mov", ".caf",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input_dir", type=Path, help="Folder containing the recordings")
    ap.add_argument("--out", type=Path, default=Path("transcripts"), help="Output folder")
    ap.add_argument("--model", default="small",
                    help="tiny / base / small / medium / large-v3 (bigger = more accurate, slower)")
    ap.add_argument("--prompt", default=None,
                    help="Hint text with names/jargon to bias spelling, e.g. 'Names: Ana, Beto'")
    ap.add_argument("--language", default=None, help="e.g. en, es. Default: auto-detect per file")
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"],
                    help="Use 'cpu' if auto picks CUDA and then crashes")
    ap.add_argument("--redo", action="store_true", help="Re-transcribe files that already have output")
    args = ap.parse_args()

    if not args.input_dir.is_dir():
        sys.exit(f"Not a folder: {args.input_dir}")

    files = sorted(p for p in args.input_dir.iterdir() if p.suffix.lower() in AUDIO_EXTS)
    if not files:
        sys.exit(f"No audio files found in {args.input_dir}")

    args.out.mkdir(parents=True, exist_ok=True)
    meta_path = args.out / "metadata.json"
    metadata = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    print(f"Loading model '{args.model}' (first run downloads it)...")
    model = WhisperModel(args.model, device=args.device, compute_type="auto")

    for i, path in enumerate(files, 1):
        out_path = args.out / f"{path.name}.json"
        if out_path.exists() and not args.redo:
            print(f"[{i}/{len(files)}] skip (done): {path.name}")
            continue

        print(f"[{i}/{len(files)}] {path.name}")
        segments, info = model.transcribe(
            str(path),
            word_timestamps=True,
            vad_filter=True,
            initial_prompt=args.prompt,
            language=args.language,
        )

        segs = []
        for seg in segments:  # generator: transcription actually happens here
            segs.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
                "words": [
                    {"start": round(w.start, 2), "end": round(w.end, 2), "word": w.word}
                    for w in (seg.words or [])
                ],
            })

        result = {
            "file": path.name,
            "duration_sec": round(info.duration, 1),
            "language": info.language,
            "segments": segs,
        }
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        entry = metadata.setdefault(path.name, {"speaker": "", "topics": []})
        entry["duration_sec"] = result["duration_sec"]
        entry["transcript"] = out_path.name
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nDone. Transcripts and metadata.json are in {args.out.resolve()}")


if __name__ == "__main__":
    main()
