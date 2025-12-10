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

    # PARÂMETROS vindos dos dropdowns personalizados
    aspect_ratio: str = Form("landscape"),
    duration: str = Form(None),
    quality: str = Form(None),

    reference_file: UploadFile | None = None,
):
    """
    Rota de geração de vídeo com Sora-2.
    """

    input_reference = reference_file.file if reference_file else None

    model_input = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": "1080p",   # qualidade padrão
    }

    if duration:
        model_input["duration"] = duration

    if quality:
        model_input["quality"] = quality

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
    """
    Rota de geração de imagem com Nano-Banana.
    """

    imgs = []
    for img in [image_1, image_2, image_3]:
        if img:
            imgs.append(img.file)

    model_input = {
        "prompt": prompt,
        "image_input": imgs,   # lista de imagens
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

    # ------------------------------------
    #         CORREÇÃO DO PARSER
    # ------------------------------------
    def extract_url(item):
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

    # DICT
    elif isinstance(output, dict):
        url = extract_url(output)
        if url:
            output_url = url

    # STRING
    elif isinstance(output, str):
        url = extract_url(output)
        if url:
            output_url = url

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
