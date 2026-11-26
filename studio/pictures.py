"""Cinematic Pixar-style 3D pictures with SDXL-Lightning (4 steps, fast on a free Colab T4) and a Pixar-style LoRA.

SDXL only reads the first 77 tokens of each prompt, so the scene (who, where, what they do) goes first and the style
goes to the second text encoder. Character consistency: each character's look is repeated in every prompt, the same seed
is used per story, and an IP-Adapter reference portrait of every main character is reused in the scenes they appear in.
"""
import gc
import re

from PIL import Image, ImageDraw, ImageFilter

STYLE = ("pixar-style, 3D animated Disney Pixar movie still, cute cartoon characters, big expressive eyes, soft cinematic "
         "lighting, vibrant colours, highly detailed")
NEGATIVE = "photo, realistic, photorealistic, ugly, deformed, bad anatomy, extra fingers, extra limbs, blurry, lowres, text, watermark, scary"
PIXAR_LORA = ("ntc-ai/SDXL-LoRA-slider.pixar-style", "pixar-style.safetensors")  # MIT licence
PIXAR_STRENGTH = 1.5
FACE_STRENGTH = 0.5  # how strongly each character's reference portrait is followed (higher = same face, less prompt freedom)


def shot_for(i, n, scene):
    speakers = list(dict.fromkeys(l.speaker for l in scene.lines if l.speaker != "Narrator"))
    if i == 0:
        return "wide establishing shot"
    if i == n - 1:
        return "wide cinematic shot, joyful ending"
    if len(speakers) == 1:
        return f"medium close-up shot of {speakers[0]}"
    return "medium two-shot, characters facing each other" if len(speakers) > 1 else "medium shot"


def present(i, story):
    """Characters that appear in scene i (named in the picture description or speaking), in order of appearance."""
    s = story.scenes[i]
    text = s.visual + " " + " ".join(l.speaker for l in s.lines)
    return [(n, lk) for n, lk in story.characters.items() if re.search(rf"\b{re.escape(n)}\b", text, re.I)]


def short_look(look, parts=2, words=14):
    """The first two phrases of a look ("a 6-year-old girl with curly hair, a yellow flower clip"), whole phrases only."""
    return " ".join(", ".join(p.strip() for p in look.replace("wearing ", "").split(",")[:parts]).split()[:words])


def prompt_parts(i, story):
    """(scene prompt for text encoder 1, style prompt for text encoder 2): the scene is never cut off by the 77-token limit."""
    s = story.scenes[i]
    shot = shot_for(i, len(story.scenes), s)
    looks = "; ".join(f"{n}: {short_look(lk)}" for n, lk in present(i, story)[:3])
    return f"{shot}, {s.visual}. {looks}", f"{STYLE}, {shot}, {s.visual}"


def prompt_for(i, story):
    """Long motion prompt for the video AI (its T5 text encoder reads long prompts)."""
    s = story.scenes[i]
    looks = ". ".join(f"{n} is {lk}" for n, lk in present(i, story))
    return (f"{s.visual}. {looks}. The characters move naturally: they talk, smile, blink and gesture with their hands, "
            "hair and clothes move softly, gentle slow camera movement. A scene from a 3D animated Pixar movie, smooth motion.")


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
        try:
            self.pipe.load_lora_weights(PIXAR_LORA[0], weight_name=PIXAR_LORA[1], adapter_name="pixar")
            self.pipe.set_adapters(["pixar"], adapter_weights=[PIXAR_STRENGTH])
        except Exception as e:  # keeps working without it
            print("Pixar-style LoRA not available, continuing without it:", e)
        self.ip = False
        if consistent:
            try:
                self.pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter_sdxl.safetensors")
                self.ip = True
            except Exception as e:  # keeps working without it
                print("IP-Adapter not available, continuing without it:", e)
        self.torch = torch

    def paint(self, prompt, w, h, seed, ref=None, prompt_2=None):
        g = self.torch.Generator("cuda").manual_seed(seed)
        extra = {"ip_adapter_image": ref or Image.new("RGB", (224, 224), "white")} if self.ip else {}
        if self.ip:
            self.pipe.set_ip_adapter_scale(FACE_STRENGTH if ref else 0.0)
        return self.pipe(prompt=prompt, prompt_2=prompt_2 or prompt, negative_prompt=NEGATIVE, width=w, height=h,
                         num_inference_steps=4, guidance_scale=0, generator=g, **extra).images[0]

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
    refs = {}
    if painter.ip:  # one reference portrait per main character, reused in every scene that character appears in
        for name, look in list(story.characters.items())[:4]:
            log(f"Designing the character {name}...")
            refs[name] = painter.paint(f"character portrait of {name}, {look}, full face, looking at the camera, plain soft background",
                                       1024, 1024, seed, prompt_2=f"{STYLE}, character design sheet, {short_look(look)}")
    out = []
    for i in range(len(story.scenes)):
        log(f"Painting scene {i + 1}/{len(story.scenes)}...")
        s = story.scenes[i]
        speakers = [l.speaker for l in s.lines if l.speaker in refs]
        main = speakers[0] if speakers else next((n for n, _ in present(i, story) if n in refs), None)
        scene, style = prompt_parts(i, story)
        out.append(painter.paint(scene, w, h, seed + i, refs.get(main), prompt_2=style))
    painter.close()
    return out
