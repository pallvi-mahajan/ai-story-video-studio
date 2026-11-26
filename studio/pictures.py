"""Cinematic Pixar-style 3D pictures with SDXL-Lightning (4 steps, fast on a free Colab T4).

Character consistency: every prompt repeats each character's exact look, uses the same seed per story, and (optionally)
an IP-Adapter reference image of the main character.
"""
import gc

from PIL import Image, ImageDraw, ImageFilter

STYLE = ("3D Pixar animation movie still, Disney Pixar character design, adorable expressive cartoon faces, big glossy eyes, "
         "soft subsurface skin, cinematic lighting, volumetric light rays, rim light, shallow depth of field, vibrant colour "
         "grading, highly detailed, octane render, masterpiece")
NEGATIVE = "photo, realistic, ugly, deformed, extra fingers, extra limbs, blurry, text, watermark, scary"


def shot_for(i, n, scene):
    speakers = list(dict.fromkeys(l.speaker for l in scene.lines if l.speaker != "Narrator"))
    if i == 0:
        return "wide establishing shot"
    if i == n - 1:
        return "wide cinematic shot, joyful ending"
    if len(speakers) == 1:
        return f"medium close-up shot of {speakers[0]}"
    return "medium two-shot, characters facing each other" if len(speakers) > 1 else "medium shot"


def prompt_for(i, story):
    s = story.scenes[i]
    text = s.visual + " " + " ".join(l.speaker for l in s.lines)
    looks = ". ".join(f"{n} is {lk}" for n, lk in story.characters.items() if n.lower() in text.lower())
    return f"{STYLE}, {shot_for(i, len(story.scenes), s)}. {s.visual}. {looks}"


class Painter:
    def __init__(self, consistent=True):
        import torch
        from diffusers import EulerDiscreteScheduler, StableDiffusionXLPipeline, UNet2DConditionModel
        from huggingface_hub import hf_hub_download
        from safetensors.torch import load_file

        base = "stabilityai/stable-diffusion-xl-base-1.0"
        unet = UNet2DConditionModel.from_config(base, subfolder="unet").to("cuda", torch.float16)
        unet.load_state_dict(load_file(hf_hub_download("ByteDance/SDXL-Lightning", "sdxl_lightning_4step_unet.safetensors"), device="cuda"))
        self.pipe = StableDiffusionXLPipeline.from_pretrained(base, unet=unet, torch_dtype=torch.float16, variant="fp16").to("cuda")
        self.pipe.scheduler = EulerDiscreteScheduler.from_config(self.pipe.scheduler.config, timestep_spacing="trailing")
        self.ip = False
        if consistent:
            try:
                self.pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter_sdxl.safetensors")
                self.pipe.set_ip_adapter_scale(0.45)
                self.ip = True
            except Exception as e:  # keeps working without it
                print("IP-Adapter not available, continuing without it:", e)
        self.torch = torch

    def paint(self, prompt, w, h, seed, ref=None):
        g = self.torch.Generator("cuda").manual_seed(seed)
        extra = {"ip_adapter_image": ref or Image.new("RGB", (224, 224), "white")} if self.ip else {}
        if self.ip:
            self.pipe.set_ip_adapter_scale(0.45 if ref else 0.0)
        return self.pipe(prompt=prompt, negative_prompt=NEGATIVE, width=w, height=h, num_inference_steps=4,
                         guidance_scale=0, generator=g, **extra).images[0]

    def close(self):
        del self.pipe
        gc.collect()
        self.torch.cuda.empty_cache()


def placeholder(i, story, w, h):
    """Used in dry-run mode (no GPU): a soft gradient card with the scene text."""
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        k = y / h
        d.line([(0, y), (w, y)], fill=(int(60 + 120 * k), int(80 + 60 * (1 - k)), int(160 - 60 * k)))
    d.ellipse([w * 0.3, h * 0.25, w * 0.7, h * 0.65], fill=(255, 220, 180))
    d.text((20, 20), f"Scene {i + 1}: {story.scenes[i].heading}", fill="white")
    return img.filter(ImageFilter.GaussianBlur(1))


def make_pictures(story, w, h, seed=7, dry_run=False, log=print):
    if dry_run:
        return [placeholder(i, story, w, h) for i in range(len(story.scenes))]
    painter = Painter()
    ref = None
    if painter.ip and story.characters:  # reference portrait of the main character, reused for every scene
        name, look = next(iter(story.characters.items()))
        log(f"Designing the main character {name}...")
        ref = painter.paint(f"{STYLE}, character portrait of {name}, {look}, plain soft background", 1024, 1024, seed)
    out = []
    for i in range(len(story.scenes)):
        log(f"Painting scene {i + 1}/{len(story.scenes)}...")
        out.append(painter.paint(prompt_for(i, story), w, h, seed + i, ref))
    painter.close()
    return out
