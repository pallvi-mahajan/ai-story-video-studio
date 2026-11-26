"""Puts it all together: scene clips stretched to the voice length, subtitles, title, crossfades, voices -> MP4."""
import subprocess

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .animate import FPS, camera_clip
from .voices import SR

FADE = 0.5


def _font(size):
    for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _wrap(draw, text, font, width):
    lines, cur = [], ""
    for w in text.split():
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = test
    return lines + [cur]


def caption(img, speaker, text, big=None):
    img = img.copy()
    d = ImageDraw.Draw(img, "RGBA")
    W, H = img.size
    if big:  # title / ending card text
        f = _font(int(min(W, H) * 0.09))
        lines = _wrap(d, big, f, W * 0.88)
        y = H * 0.18
        for l in lines:
            tw = d.textlength(l, font=f)
            d.text(((W - tw) / 2, y), l, font=f, fill="#fff3c4", stroke_width=max(3, int(f.size * 0.08)), stroke_fill="#3b1a6b")
            y += f.size * 1.15
    if text:
        f = _font(int(min(W, H) * 0.045))
        lines = _wrap(d, text, f, W * 0.82)[:3]
        named = speaker and speaker != "Narrator"
        box_h = f.size * 1.3 * len(lines) + f.size * (1.7 if named else 0.8)
        y0 = H * 0.8 - box_h / 2
        d.rounded_rectangle([W * 0.06, y0, W * 0.94, y0 + box_h], radius=f.size // 2, fill=(0, 0, 0, 130))
        y = y0 + f.size * 0.4
        if named:
            sf = _font(int(f.size * 0.85))
            d.text(((W - d.textlength(speaker, font=sf)) / 2, y), speaker, font=sf, fill="#ffd65a")
            y += f.size * 1.2
        for l in lines:
            d.text(((W - d.textlength(l, font=f)) / 2, y), l, font=f, fill="white")
            y += f.size * 1.3
    return img


def fit(frames, n):
    """Make a clip n frames long: play the AI motion once, then hold the last frame with a slow camera push-in
    (playing it backwards made characters move in reverse)."""
    if not frames or len(frames) >= n:
        return frames[:n]
    out = frames + camera_clip(frames[-1].convert("RGB"), (n - len(frames)) / FPS, 0)
    return (out + out[-1:] * n)[:n]


def build_video(story, clips, audios, size, out_path, log=print):
    """clips: list of frame lists; audios: list of (samples, cues) per scene."""
    W, H = size
    writer = imageio_ffmpeg.write_frames(out_path + ".silent.mp4", (W, H), fps=FPS, codec="libx264", quality=8,
                                         macro_block_size=1, output_params=["-pix_fmt", "yuv420p"])
    writer.send(None)
    tracks, t_total, prev_tail = [], 0.0, None
    n_sc = len(story.scenes)
    for i, (frames, (samples, cues)) in enumerate(zip(clips, audios)):
        lead = 2.0 if i == 0 else 0.0
        tail = 2.5 if i == n_sc - 1 else 0.0
        dur = max(3.5, len(samples) / SR + 0.6) + lead + tail
        n = int(dur * FPS)
        frames = [f.convert("RGB").resize((W, H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
                  for f in fit(frames, n)]
        log(f"Composing scene {i + 1}/{n_sc} ({dur:.1f}s)...")
        for k, fr in enumerate(frames):
            t = k / FPS
            cue = next((c for c in cues if c[0] + lead <= t <= c[1] + lead + 0.15), None)
            big = story.title if (i == 0 and t < 3.0) else (story.ending if (i == n_sc - 1 and t > dur - 2.5) else None)
            fr = caption(fr, cue[2] if cue else None, cue[3] if cue else None, big)
            if prev_tail is not None and k < int(FADE * FPS):  # crossfade from the previous scene
                a = k / (FADE * FPS)
                fr = Image.blend(prev_tail, fr, a)
            if i == 0 and k < FPS // 2:  # fade in from black
                fr = Image.blend(Image.new("RGB", (W, H)), fr, k / (FPS / 2))
            if i == n_sc - 1 and k > n - FPS:  # fade out to black
                fr = Image.blend(Image.new("RGB", (W, H)), fr, max(0, (n - k) / FPS))
            writer.send(np.asarray(fr))
        prev_tail = frames[-1]
        pad = np.zeros(int(lead * SR), np.float32)
        track = np.concatenate([pad, samples])
        track = np.concatenate([track, np.zeros(max(0, int(dur * SR) - len(track)), np.float32)])[: int(dur * SR)]
        tracks.append(track)
        t_total += dur
    writer.close()
    audio = np.concatenate(tracks)
    audio = (audio / max(1e-6, np.abs(audio).max()) * 0.9 * 32767).astype(np.int16)
    import wave

    with wave.open(out_path + ".wav", "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(audio.tobytes())
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", out_path + ".silent.mp4", "-i", out_path + ".wav",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", out_path], check=True)
    return t_total
