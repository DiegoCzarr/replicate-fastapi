import os
import replicate
import requests
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

# Auth
os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPLICATE_API_TOKEN")

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jobodega.webflow.io",
        "https://www.jobodega.com",
        "https://jobodega.com",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
#                  SORA 2 - VIDEO
# =====================================================

@app.post("/generate")
async def generate_video(
    prompt: str = Form(...),

    # Parâmetros vindos dos dropdowns
    aspect_ratio: str = Form("16:9"),
    duration: str = Form(None),
    quality: str = Form("1080p"),

    # Arquivo opcional (define se é image+text)
    reference_file: UploadFile | None = None,
):
    """
    Geração de vídeo Sora-2.
    Suporta:
    - Texto puro
    - Imagem + texto
    """

    # Se veio arquivo → modo imagem + texto
    input_reference = reference_file.file if reference_file else None

    model_input = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": "1080p",
    }

    if duration:
        model_input["duration"] = duration

    if quality:
        model_input["quality"] = quality

    # Aqui aplicamos o input_reference apenas se tiver imagem
    if input_reference:
        model_input["input_reference"] = input_reference

    prediction = replicate.predictions.create(
        model="openai/sora-2",
        input=model_input
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }

from typing import List
import tempfile

# =====================================================
#               SORA 2 PRO - VIDEO
# =====================================================

@app.post("/generate-sora-pro")
async def generate_sora_pro(
    prompt: str = Form(...)
):
    """
    Geração de vídeo com Sora-2 Pro
    - Texto puro
    - Input simples (apenas prompt)
    """

    prediction = replicate.predictions.create(
        model="openai/sora-2-pro",
        input={
            "prompt": prompt
        }
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }

# =====================================================
#               KLING 2.5 PRO - VIDEO
# =====================================================

@app.post("/generate-kling-2.5-pro")
async def generate_kling_video(
    prompt: str = Form(...)
):
    """
    Kling v2.5 Turbo Pro
    - Text → Video
    """

    model_input = {
        "prompt": prompt
    }

    prediction = replicate.predictions.create(
        model="kwaivgi/kling-v2.5-turbo-pro",
        input=model_input
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }

# =====================================================
#               GEN 4 TURBO - VIDEO
# =====================================================

@app.post("/generate-gen4")
async def generate_gen4_video(
    prompt: str = Form(...),
    image: UploadFile = Form(...)
):
    """
    Runway Gen-4 Turbo
    - Image REQUIRED
    - Prompt REQUIRED
    """

    # Save image temporarily
    suffix = os.path.splitext(image.filename)[1] or ".png"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(await image.read())
    tmp.close()

    model_input = {
        "image": tmp.name,
        "prompt": prompt
    }

    prediction = replicate.predictions.create(
        model="runwayml/gen4-turbo",
        input=model_input
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }

# =====================================================
#                GOOGLE VEO 3.1 - VIDEO
# =====================================================

@app.post("/generate-veo")
async def generate_veo_video(
    prompt: str = Form(...),

    # imagens de referência (0 a N)
    reference_images: List[UploadFile] = Form([]),
):
    """
    Geração de vídeo com Google Veo 3.1
    - Texto puro
    - Texto + múltiplas imagens
    """

    image_files = []

    # salva imagens temporárias
    for img in reference_images:
        suffix = os.path.splitext(img.filename)[1] or ".png"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(await img.read())
        tmp.close()
        image_files.append(tmp.name)

    model_input = {
        "prompt": prompt,
    }

    if image_files:
        model_input["reference_images"] = image_files

    prediction = replicate.predictions.create(
        model="google/veo-3.1",
        input=model_input
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }

@app.post("/generate-veo-fast")
async def generate_veo_fast(
    prompt: str = Form(...),
    resolution: str = Form("720p"),
    image: UploadFile = Form(...)
):
    """
    Google Veo 3 Fast
    - Image REQUIRED
    - Prompt REQUIRED
    """

    # Save image temporarily
    suffix = os.path.splitext(image.filename)[1] or ".png"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(await image.read())
    tmp.close()

    model_input = {
        "image": tmp.name,
        "prompt": prompt,
        "resolution": resolution
    }

    prediction = replicate.predictions.create(
        model="google/veo-3-fast",
        input=model_input
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }


# =====================================================
#                NANO-BANANA - IMAGEM
# =====================================================

@app.post("/generate-image")
async def generate_image(
    prompt: str = Form(...),
    quality: str = Form("standard"),
    image_1: UploadFile | None = None,
    image_2: UploadFile | None = None,
    image_3: UploadFile | None = None,
):
    imgs = [img.file for img in [image_1, image_2, image_3] if img]

    model_input = {
        "prompt": prompt,
        "image_input": imgs,
        "quality": quality
    }

    prediction = replicate.predictions.create(
        model="google/nano-banana",
        input=model_input
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }

@app.post("/generate-nano-pro")
async def generate_nano_banana_pro(
    prompt: str = Form(...),
    aspect_ratio: str = Form("1:1"),
    output_format: str = Form("png")
):
    """
    Nano Banana Pro
    """

    model_input = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": output_format
    }

    prediction = replicate.predictions.create(
        model="google/nano-banana-pro",
        input=model_input
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }

# =====================================================
#           SEEDREAM 4.5 - IMAGE
# =====================================================

@app.post("/generate-seedream-4.5")
async def generate_seedream(
    prompt: str = Form(...),
    size: str = Form("2K"),
    aspect_ratio: str = Form("1:1")
):
    prediction = replicate.predictions.create(
        model="bytedance/seedream-4.5",
        input={
            "prompt": prompt,
            "size": size,
            "aspect_ratio": aspect_ratio
        }
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }
# =====================================================
#        FLUX KONTEXT MAX - IMAGE + TEXT
# =====================================================

@app.post("/generate-flux-kontext")
async def generate_flux_kontext(
    prompt: str = Form(...),
    output_format: str = Form("jpg"),
    input_image: UploadFile = File(...)
):
    """
    Flux Kontext Max
    Texto + imagem obrigatória
    """

    # 1️⃣ Ler os bytes da imagem
    image_bytes = await input_image.read()

    # 2️⃣ Criar prediction corretamente
    prediction = replicate.predictions.create(
        model="black-forest-labs/flux-kontext-max",
        input={
            "prompt": prompt,
            "image": image_bytes,   # ⚠️ nome correto
            "output_format": output_format
        }
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }

# =====================================================
#               FLUX 2 PRO - IMAGE
# =====================================================

@app.post("/generate-flux-2-pro")
async def generate_flux_2_pro(
    prompt: str = Form(...)
):
    prediction = replicate.predictions.create(
        model="black-forest-labs/flux-2-pro",
        input={
            "prompt": prompt
        }
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }


# =====================================================
#              FLUX 1.1 PRO - IMAGE
# =====================================================

@app.post("/generate-flux")
async def generate_flux(
    prompt: str = Form(...),
    prompt_upsampling: bool = Form(False)
):
    prediction = replicate.predictions.create(
        model="black-forest-labs/flux-1.1-pro",
        input={
            "prompt": prompt,
            "prompt_upsampling": prompt_upsampling
        }
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }


# =====================================================
#                     STATUS / POLLING
# =====================================================

@app.get("/status/{prediction_id}")
async def prediction_status(prediction_id: str):
    prediction = replicate.predictions.get(prediction_id)

    output_url = None
    output = prediction.output

    def extract_url(item):
        """Extrai URL válida de vídeo ou imagem."""
        if not item:
            return None

        if isinstance(item, str):
            if item.endswith((".mp4", ".jpg", ".png", ".jpeg", ".webp")):
                return item

        if isinstance(item, dict):
            for key in ["video", "output", "url", "image", "output_video"]:
                u = item.get(key)
                if isinstance(u, str) and u.endswith((".mp4", ".jpg", ".png", ".jpeg", ".webp")):
                    return u
        return None

    # LISTA
    if isinstance(output, list):
        for item in output:
            url = extract_url(item)
            if url:
                output_url = url
                break

    # DICIONÁRIO
    elif isinstance(output, dict):
        output_url = extract_url(output)

    # STRING
    elif isinstance(output, str):
        output_url = extract_url(output)

    print("DEBUG OUTPUT:", output)
    print("FINAL URL:", output_url)

    return {
        "id": prediction.id,
        "status": prediction.status,
        "output_url": output_url,
        "logs": prediction.logs,
    }


# =====================================================
#                   DOWNLOAD OPCIONAL
# =====================================================

@app.get("/download/{prediction_id}")
async def download_prediction(prediction_id: str):
    prediction = replicate.predictions.get(prediction_id)

    if not prediction.output:
        return {"error": "Output ainda não está pronto."}

    output_url = prediction.output[0]
    file_bytes = requests.get(output_url).content

    file_path = f"output_{prediction_id}.mp4"
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    return {"file_path": file_path, "downloaded": True}
