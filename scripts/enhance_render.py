#!/usr/bin/env python3
"""Take a BIM viewer screenshot and generate an AI concept render.

Uses FAL image generation (flux/sdxl) with the screenshot as image-to-image
input, applying an architectural concrete style.

Usage:
    # From a screenshot file:
    python scripts/enhance_render.py screenshot.png -o concept.png

    # Pipeline: capture from the IFC viewer first, then enhance:
    # (In viewer, click 📷 Screenshot or ✨ AI Render to save)
    python scripts/enhance_render.py bim2print-view-for-ai.png

Requires: pip install requests pillow
"""

import argparse
import base64
import json
import os
import sys
import requests
from io import BytesIO
from PIL import Image


FAL_KEY = os.environ.get("FAL_KEY", "")


def encode_image(path_or_url: str) -> str:
    """Read image file or fetch URL, return base64 data URI."""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        resp = requests.get(path_or_url, timeout=30)
        resp.raise_for_status()
        img_data = resp.content
    else:
        with open(path_or_url, "rb") as f:
            img_data = f.read()

    # Resize if too large (FAL has size limits)
    img = Image.open(BytesIO(img_data))
    w, h = img.size
    max_dim = 1536
    if max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="PNG")
        img_data = buf.getvalue()

    b64 = base64.b64encode(img_data).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def generate_concept(
    input_image: str,
    prompt: str = (
        "A modern 3D-printed concrete house, warm afternoon sunlight, "
        "architectural photography, photorealistic, highly detailed concrete texture, "
        "clean minimalist design, volumetric lighting, depth of field, "
        "cinematic composition, 8K, professional architectural photography"
    ),
    negative_prompt: str = (
        "cartoon, low quality, blurry, distorted, deformed, "
        "watermark, text, signature, low resolution, oversaturated"
    ),
    strength: float = 0.7,
    output_path: str = "concept_render.png",
) -> str:
    """Send to FAL image-to-image and save result."""

    if not FAL_KEY:
        print("⚠️  FAL_KEY not set. Set FAL_KEY=<your_key> in environment.")
        print("   Falling back: saving prompt data so you can run manually.")
        with open("concept_prompt.json", "w") as f:
            json.dump({
                "input_image": input_image[:80] + "...",
                "prompt": prompt,
                "strength": strength,
                "output_path": output_path,
            }, f, indent=2)
        print(f"   Saved request data to concept_prompt.json")
        return None

    print(f"📤 Sending to FAL...")

    headers = {
        "Authorization": f"Key {FAL_KEY}",
        "Content-Type": "application/json",
    }

    # Try flux-pro first (best quality), fall back to other models
    models = [
        {
            "name": "fal-ai/flux-pro/v1.1-ultra",
            "payload": {
                "image_url": input_image,
                "prompt": prompt,
                "strength": strength,
                "guidance_scale": 3.5,
                "num_inference_steps": 28,
                "image_size": "square_hd",
            }
        },
        {
            "name": "fal-ai/flux/dev",
            "payload": {
                "image_url": input_image,
                "prompt": prompt,
                "strength": strength,
                "guidance_scale": 3.5,
                "num_inference_steps": 28,
                "image_size": "landscape_4_3",
            }
        },
        {
            "name": "fal-ai/stable-diffusion-v3-medium",
            "payload": {
                "image_url": input_image,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "strength": strength,
                "guidance_scale": 5.0,
                "num_inference_steps": 30,
            }
        },
    ]

    for model in models:
        endpoint = f"https://fal.run/{model['name']}"
        payload = model["payload"]
        payload["enable_safety_checker"] = False

        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=120)
            if resp.status_code == 200:
                result = resp.json()
                image_url = result.get("images", [{}])[0].get("url", result.get("image", {}).get("url"))
                if image_url:
                    print(f"  ✅ Concept render generated!")
                    img_resp = requests.get(image_url, timeout=30)
                    with open(output_path, "wb") as f:
                        f.write(img_resp.content)
                    print(f"  📁 Saved to {output_path}")
                    return output_path
                else:
                    print(f"  ⚠️  No image URL in response: {json.dumps(result)[:200]}")
            else:
                print(f"  ⚠️  {model['name']} returned {resp.status_code}: {resp.text[:150]}")

        except Exception as e:
            print(f"  ⚠️  {model['name']} error: {e}")

    print("❌ All models failed. Check FAL_KEY and network.")
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate AI concept render from BIM viewer screenshot"
    )
    parser.add_argument("input", help="Input image path (screenshot from IFC viewer)")
    parser.add_argument("-o", "--output", default="concept_render.png",
                        help="Output PNG path")
    parser.add_argument("--prompt", default=None,
                        help="Custom prompt (optional)")
    parser.add_argument("--strength", type=float, default=0.7,
                        help="Image-to-image strength 0-1 (default: 0.7)")
    parser.add_argument("--style", choices=["modern", "brutalist", "warm", "sustainable"],
                        default="modern",
                        help="Architectural style preset")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        sys.exit(1)

    print(f"🎨 Loading input image: {args.input}")
    img = Image.open(args.input)
    print(f"   Size: {img.size[0]} × {img.size[1]} px")

    # Style presets
    style_prompts = {
        "modern": (
            "A modern 3D-printed concrete house, warm afternoon sunlight, "
            "architectural photography, photorealistic, highly detailed concrete texture, "
            "clean minimalist design, volumetric lighting, depth of field, "
            "cinematic composition, 8K, professional architectural photography"
        ),
        "brutalist": (
            "Raw brutalist concrete architecture, dramatic shadows, "
            "high contrast lighting, textured exposed concrete surfaces, "
            "moody sky, architectural photography, monochromatic tones, sharp details, "
            "cinematic, 8K, masterpiece"
        ),
        "warm": (
            "Warm sunset lighting on a concrete building, golden hour, "
            "soft shadows, warm ambient glow, modern residential architecture, "
            "3D-printed concrete walls, photorealistic, detailed textures, "
            "professional architectural photography, cinematic"
        ),
        "sustainable": (
            "Eco-friendly 3D-printed concrete home, green surroundings, "
            "native garden integration, sustainable architecture, "
            "natural lighting, photorealistic, detailed, warm inviting atmosphere, "
            "architectural photography, 8K"
        ),
    }

    prompt = args.prompt or style_prompts.get(args.style, style_prompts["modern"])

    print(f"🎯 Prompt: {prompt[:100]}...")
    print(f"🎯 Style: {args.style}")

    encoded = encode_image(args.input)
    result = generate_concept(encoded, prompt=prompt, strength=args.strength, output_path=args.output)

    if result:
        print(f"\n✅ Done! Open {result} to view the concept render.")
        print(f"\n💡 Tip: Try different styles: --style brutalist --style warm --style sustainable")
        print(f"   Adjust strength: --strength 0.5 (closer to original) / 0.85 (more creative)")
    else:
        print(f"\n⚠️  Concept generation incomplete. See errors above.")


if __name__ == "__main__":
    main()
