"""Builds colab/AI_Story_Video_Studio.ipynb (python tools/make_notebook.py)."""
import json
from pathlib import Path

md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s.strip()}
code = lambda s: {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip()}

cells = [
    md("""
# AI Story Video Studio (free, Pixar-style AI video)

Type a theme (e.g. *Mia learns how to share her toys*) or paste a full scene script and get a finished kids story video:
**AI 3D-animation-style pictures -> AI motion (LTX-Video) -> character voices -> subtitles -> MP4**.

1. Menu **Runtime -> Change runtime type -> T4 GPU -> Save**.
2. Run the cells from top to bottom (press ▶ on each). Type your own story in cell 2, then press ▶ on cell 2.
3. First run: about 10 min of setup/downloads. A 6-scene video then takes roughly 15-30 min on the free GPU.

Needs a normal internet connection (home Wi-Fi / mobile data). Office networks that block AI sites will not work.
"""),
    code("""
#@title 1. Setup (one time per session)
!nvidia-smi --query-gpu=name,memory.total --format=csv
!git clone -q https://github.com/pallvi-mahajan/ai-story-video-studio.git /content/studio_repo 2>/dev/null || (cd /content/studio_repo && git pull -q)
%cd /content/studio_repo
!pip install -q -r requirements-colab.txt
print("Setup done")
"""),
    code('''
#@title 2. Your story -> make the video
#@markdown Replace the example with your own theme (e.g. *Inayat learns how to make rice at the age of 9*), or paste a full script
#@markdown with "Scene 1", "Visual prompt:", "Narration:", "Dialogue:" lines. Then press ▶ on this cell.
STORY = """
Mia learns how to share her toys
"""
#@markdown Optional: your characters, one per line as `Name: how they look`. The same look is used in every scene.
CHARACTERS = """
"""
SCENES = 6  #@param {type:"slider", min:3, max:10, step:1}
FORMAT = "16:9"  #@param ["16:9", "9:16", "1:1"]
ANIMATION = "ltx"  #@param ["ltx", "camera", "svd"]
#@markdown **ltx** = real AI motion (slow, best). **camera** = cinematic camera moves only (fast). **svd** needs a Hugging Face token.
SEED = 7  #@param {type:"integer"}

import os
from IPython.display import Video, display
from studio.run import make_video
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
out = make_video(STORY, CHARACTERS, SCENES, FORMAT, ANIMATION, SEED, out_dir="/content/output")
display(Video(out, embed=True, width=640))
'''),
    code("""
#@title 3. Download the video and the scene pictures
from google.colab import files
import glob
files.download(out)
for p in sorted(glob.glob("/content/output/scene_*.png")):
    files.download(p)
"""),
]
for c in cells:
    c["source"] = [l + "\n" for l in c["source"].split("\n")]
    c["source"][-1] = c["source"][-1].rstrip("\n")
nb = {"nbformat": 4, "nbformat_minor": 0, "cells": cells,
      "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"}, "kernelspec": {"name": "python3", "display_name": "Python 3"}}}
out = Path(__file__).resolve().parent.parent / "colab" / "AI_Story_Video_Studio.ipynb"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(nb, indent=1))
print("wrote", out)
