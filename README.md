# AI Story Video Studio

Free kids story video maker, two ways. Type a theme like *"Mia learns how to share her toys"* (or paste a full scene
script) and get a finished video with characters, voices, subtitles and a moral.

| | **A. AI video (Google Colab)** | **B. 3D in the browser** |
|---|---|---|
| Look | Pixar-style AI 3D pictures + AI motion (closest to YouTube AI story channels) | Real-time 3D cartoon characters (toy-like, game style) |
| Where | Free Google Colab GPU | Any browser: https://pallvi-mahajan.github.io/ai-story-video-studio/ |
| Network | Home Wi-Fi / mobile data (office networks that block AI sites won't work) | Works on any network, also offices |
| Speed | ~15-30 min for 6 scenes | ~1-2 min |
| Login | Google account (for Colab) | None |

## A. AI video on Google Colab
1. Open https://colab.research.google.com/github/pallvi-mahajan/ai-story-video-studio/blob/main/colab/AI_Story_Video_Studio.ipynb
2. **Runtime -> Change runtime type -> T4 GPU -> Save**.
3. Run the 4 cells. Cell 2 is where you type your theme/script and characters.

Pipeline (`studio/`): built-in story writer or script parser -> SDXL-Lightning + Pixar-style LoRA pictures (scene-first
prompts so the scene is never cut off, same seed, same character descriptions, and an IP-Adapter reference portrait
per main character for consistent faces) -> LTX-Video 0.9.5 image-to-video, 4-second clips (AI motion; falls back to
LTX-Video 0.9, then to camera moves) -> Kokoro voices (a voice per character) -> subtitles, title, crossfades,
sharpening -> MP4.

Tuning (top of `studio/pictures.py`): `PIXAR_STRENGTH` (cartoon look, default 1.5) and `FACE_STRENGTH` (how closely
each character keeps the same face, default 0.5).

Test the pipeline without a GPU: `python -m studio.run "Mia learns how to share her toys" --dry-run`

## B. Browser 3D (folder `docs/`)
Story writer, 3D characters built from descriptions, 3D worlds from scene text, animation (blink, talk, walk, wave,
jump), voices, subtitles, music, step-by-step scene checking. Hosted with GitHub Pages from `docs/`.

## Licences
SDXL (CreativeML Open RAIL++-M), SDXL-Lightning (OpenRAIL++), Pixar-style LoRA slider by ntc-ai (MIT), IP-Adapter (Apache-2.0), LTX-Video (LTXV Open Weights
licence: check it before commercial use), Kokoro-82M (Apache-2.0), Three.js (MIT).
