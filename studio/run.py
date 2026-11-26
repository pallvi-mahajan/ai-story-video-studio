"""One call: theme or script -> story -> Pixar-style AI pictures -> AI animation -> voices -> finished MP4."""
import argparse
import os
import time

from .animate import animate_all
from .assemble import build_video
from .pictures import make_pictures, prompt_for
from .story import load_story, parse_characters
from .voices import assign_voices, scene_audio

SIZES = {"9:16": (720, 1280, 768, 1344), "16:9": (1280, 720, 1344, 768), "1:1": (1024, 1024, 1024, 1024)}


def make_video(text, characters="", scenes=6, fmt="16:9", engine="ltx", seed=7, out_dir="output", dry_run=False, log=print):
    t0 = time.time()
    os.makedirs(out_dir, exist_ok=True)
    story = load_story(text, scenes, parse_characters(characters))
    log(f"Story: {story.title} | {len(story.scenes)} scenes | characters: {', '.join(story.characters) or 'narrator'}")
    for i, s in enumerate(story.scenes):
        log(f"  {i + 1}. {s.heading}: " + " / ".join(f"{l.speaker}: {l.text}" for l in s.lines)[:160])
    W, H, pw, ph = SIZES[fmt]
    pictures = make_pictures(story, pw, ph, seed, dry_run, log)
    for i, p in enumerate(pictures):
        p.save(os.path.join(out_dir, f"scene_{i + 1}.png"))
    prompts = [prompt_for(i, story) for i in range(len(story.scenes))]
    clips = animate_all(pictures, prompts, "camera" if dry_run else engine, seed, log)
    log("Creating voices...")
    voices = assign_voices(story.characters)
    audios = [scene_audio(s.lines, voices) for s in story.scenes]
    name = "".join(c if c.isalnum() else "-" for c in story.title.lower()).strip("-") or "story"
    out = os.path.join(out_dir, f"{name}.mp4")
    seconds = build_video(story, clips, audios, (W, H), out, log)
    log(f"Done: {out} ({seconds:.0f}s video, made in {(time.time() - t0) / 60:.1f} min)")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("text")
    ap.add_argument("--characters", default="")
    ap.add_argument("--scenes", type=int, default=6)
    ap.add_argument("--format", default="16:9", choices=list(SIZES))
    ap.add_argument("--engine", default="ltx", choices=["ltx", "svd", "camera"])
    ap.add_argument("--dry-run", action="store_true", help="no GPU: placeholder pictures + camera moves (tests the pipeline)")
    a = ap.parse_args()
    make_video(a.text, a.characters, a.scenes, a.format, a.engine, out_dir="output", dry_run=a.dry_run)
