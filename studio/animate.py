"""Turns each still picture into a moving clip.

engines:
  "ltx"    - LTX-Video 0.9.5 image-to-video (open, no login; falls back to LTX-Video 0.9). Real AI motion: characters move,
             hair, light, camera. 4-second clips.
  "svd"    - Stable Video Diffusion XT (needs a free Hugging Face token with the model licence accepted).
  "camera" - no AI: smooth cinematic camera move on the picture (fast, always works).
If an AI engine fails (memory, download...), that scene falls back to "camera" so the video is always finished.
"""
import gc

import numpy as np
from PIL import Image

FPS = 24


def camera_clip(img, seconds=3.0, move=0, size=None):
    w, h = size or img.size
    n = int(seconds * FPS)
    base = img.resize((int(w * 1.25), int(h * 1.25)), Image.LANCZOS)
    W, H = base.size
    frames = []
    for k in range(n):
        p = k / max(1, n - 1)
        e = p * p * (3 - 2 * p)
        z = [1.0 + 0.2 * e, 1.2 - 0.2 * e, 1.1, 1.1][move % 4]
        cw, ch = W / z, H / z
        px = [0.5, 0.5, 0.2 + 0.6 * e, 0.8 - 0.6 * e][move % 4]
        x = (W - cw) * px
        y = (H - ch) * 0.45
        frames.append(base.crop((int(x), int(y), int(x + cw), int(y + ch))).resize((w, h), Image.LANCZOS))
    return frames


class LTX:
    def __init__(self):
        import torch
        from transformers import BitsAndBytesConfig, T5EncoderModel

        def load(repo, pipeline_cls):
            te = T5EncoderModel.from_pretrained(repo, subfolder="text_encoder", torch_dtype=torch.float16,
                                                quantization_config=BitsAndBytesConfig(load_in_8bit=True))
            return pipeline_cls.from_pretrained(repo, text_encoder=te, torch_dtype=torch.float16)

        try:
            from diffusers import LTXConditionPipeline

            self.pipe, self.new = load("Lightricks/LTX-Video-0.9.5", LTXConditionPipeline), True
        except Exception as e:
            print("LTX-Video 0.9.5 not available, using LTX-Video 0.9:", e)
            from diffusers import LTXImageToVideoPipeline

            self.pipe, self.new = load("Lightricks/LTX-Video", LTXImageToVideoPipeline), False
        self.pipe.transformer.to("cuda")
        self.pipe.vae.to("cuda")
        self.pipe.vae.enable_tiling()
        self.torch = torch

    def clip(self, img, prompt, seed):
        w, h = (768, 448) if img.width >= img.height else (448, 768)
        img = img.resize((w, h), Image.LANCZOS)
        args = dict(prompt=prompt, negative_prompt="worst quality, blurry, jittery, distorted, deformed face, morphing, flicker",
                    width=w, height=h, num_frames=97, num_inference_steps=30, guidance_scale=3.0,
                    decode_timestep=0.05, decode_noise_scale=0.025, generator=self.torch.Generator("cuda").manual_seed(seed))
        if self.new:
            from diffusers.pipelines.ltx.pipeline_ltx_condition import LTXVideoCondition

            return self.pipe(conditions=[LTXVideoCondition(image=img, frame_index=0)], **args).frames[0]
        return self.pipe(image=img, **args).frames[0]

    def close(self):
        del self.pipe
        gc.collect()
        self.torch.cuda.empty_cache()


class SVD:
    def __init__(self):
        import torch
        from diffusers import StableVideoDiffusionPipeline

        self.pipe = StableVideoDiffusionPipeline.from_pretrained("stabilityai/stable-video-diffusion-img2vid-xt",
                                                                 torch_dtype=torch.float16, variant="fp16")
        self.pipe.enable_model_cpu_offload()
        self.torch = torch

    def clip(self, img, prompt, seed):
        w, h = (1024, 576) if img.width >= img.height else (576, 1024)
        return self.pipe(img.resize((w, h)), decode_chunk_size=4, num_frames=25, motion_bucket_id=100, noise_aug_strength=0.02,
                         generator=self.torch.Generator("cuda").manual_seed(seed)).frames[0]

    def close(self):
        del self.pipe
        gc.collect()
        self.torch.cuda.empty_cache()


def animate_all(pictures, prompts, engine="ltx", seed=7, log=print):
    """Returns one list of PIL frames per scene."""
    model = None
    if engine in ("ltx", "svd"):
        try:
            log(f"Loading the AI animation model ({engine.upper()})... (first time takes a few minutes)")
            model = LTX() if engine == "ltx" else SVD()
        except Exception as e:
            log(f"Could not load the {engine.upper()} model ({e}). Using cinematic camera moves instead.")
    clips = []
    for i, (img, prompt) in enumerate(zip(pictures, prompts)):
        if model:
            try:
                log(f"Animating scene {i + 1}/{len(pictures)} with AI...")
                clips.append(model.clip(img, prompt, seed + i))
                continue
            except Exception as e:
                log(f"Scene {i + 1}: AI animation failed ({e}); using a camera move.")
                model.torch.cuda.empty_cache()
        clips.append(camera_clip(img, 4.0, i))
    if model:
        model.close()
    return clips
