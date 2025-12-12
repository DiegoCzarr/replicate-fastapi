import os
import replicate
import requests
from fastapi import FastAPI, UploadFile, Form
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
