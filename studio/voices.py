"""Character voices with Kokoro-82M (free, open). Each speaker gets a consistent voice."""
import re

import numpy as np

SR = 24000
NARRATOR = "af_heart"
FEMALE = ["af_bella", "af_nicole", "af_sarah", "bf_emma"]
MALE = ["am_puck", "am_michael", "am_fenrir", "bm_george"]
ELDER_F, ELDER_M = "bf_emma", "bm_george"
_pipes = {}


def assign_voices(characters: dict) -> dict:
    voices, f, m = {"Narrator": NARRATOR}, 0, 0
    for name, look in characters.items():
        t = f" {look.lower()} {name.lower()} "
        male = re.search(r"\b(boy|man|grandpa|grandfather|father|dad|king|prince|brother|uncle)\b", t)
        elder = re.search(r"grandma|grandmother|grandpa|grandfather|granny", t)
        if elder:
            voices[name] = ELDER_M if male else ELDER_F
        elif male:
            voices[name] = MALE[m % len(MALE)]
            m += 1
        else:
            voices[name] = FEMALE[f % len(FEMALE)]
            f += 1
    return voices


def _pipe(lang):
    from kokoro import KPipeline

    if lang not in _pipes:
        shared = next(iter(_pipes.values())).model if _pipes else True
        _pipes[lang] = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M", model=shared)
    return _pipes[lang]


def speak(text: str, voice: str, speed: float = 1.0) -> np.ndarray:
    chunks = [r.audio.numpy() for r in _pipe(voice[0])(text, voice=voice, speed=speed) if r.audio is not None]
    return np.concatenate(chunks) if chunks else np.zeros(int(SR * 0.5), np.float32)


def scene_audio(lines, voices: dict):
    """Returns (samples, cues) for one scene. cues = [(start_s, end_s, speaker, text)]."""
    parts, cues, t = [], [], 0.3
    parts.append(np.zeros(int(SR * 0.3), np.float32))
    for i, line in enumerate(lines):
        voice = voices.get(line.speaker, FEMALE[0])
        audio = speak(line.text, voice, 0.95 if line.speaker == "Narrator" else 1.05)
        cues.append((t, t + len(audio) / SR, line.speaker, line.text))
        gap = 0.25 if i + 1 < len(lines) and lines[i + 1].speaker == line.speaker else 0.45
        parts += [audio, np.zeros(int(SR * gap), np.float32)]
        t += len(audio) / SR + gap
    return np.concatenate(parts), cues
