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

# CORS CORRETO
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
#                CREATE VIDEO PREDICTION
# =====================================================

@app.post("/generate")
async def generate_video(
    prompt: str = Form(...),

    # NOVOS PARAMETROS
    aspect_ratio: str = Form("landscape"),
    duration: str = Form(None),
    quality: str = Form(None),

    reference_file: UploadFile | None = None,
):
    """
    Recebe prompt, imagem opcional, e parâmetros do dropdown.
    """

    # Se tiver imagem, converte para file-like object (Replicate aceita)
    input_reference = None
    if reference_file is not None:
        input_reference = reference_file.file

    # -----------------------------
    # INPUT ENVIADO PARA O MODELO
    # -----------------------------
    model_input = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": "1080p",     # padrão solicitado
    }

    # Adiciona parâmetros SOMENTE se foram enviados
    if duration:
        model_input["duration"] = duration

    if quality:
        model_input["quality"] = quality

    if input_reference:
        model_input["input_reference"] = input_reference

    # -----------------------------
    # CRIA PREDIÇÃO
    # -----------------------------
    prediction = replicate.predictions.create(
        model="openai/sora-2",   # seu modelo atual
        input=model_input
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }


# =====================================================
#                       POLLING
# =====================================================

@app.get("/status/{prediction_id}")
async def prediction_status(prediction_id: str):
    prediction = replicate.predictions.get(prediction_id)

    output_url = None
    output = prediction.output

    # output pode vir em vários formatos — tratamos todos
    if isinstance(output, str):
        if output.endswith(".mp4"):
            output_url = output

    elif isinstance(output, list):
        for item in output:
            if isinstance(item, str) and item.endswith(".mp4"):
                output_url = item
                break
            if isinstance(item, dict):
                url = item.get("video") or item.get("output") or item.get("url")
                if isinstance(url, str) and url.endswith(".mp4"):
                    output_url = url
                    break

    elif isinstance(output, dict):
        url = (
            output.get("video")
            or output.get("output")
            or output.get("url")
            or output.get("output_video")
        )
        if isinstance(url, str) and url.endswith(".mp4"):
            output_url = url

    print("DEBUG OUTPUT:", output)
    print("VIDEO URL:", output_url)

    return {
        "id": prediction.id,
        "status": prediction.status,
        "logs": prediction.logs,
        "output_url": output_url
    }


# =====================================================
#                     DOWNLOAD OPCIONAL
# =====================================================

@app.get("/download/{prediction_id}")
async def download_prediction(prediction_id: str):
    prediction = replicate.predictions.get(prediction_id)

    if not prediction.output:
        return {"error": "Output ainda não está pronto."}

    output_url = prediction.output[0]
    video_bytes = requests.get(output_url).content

    file_path = f"output_{prediction_id}.mp4"
    with open(file_path, "wb") as f:
        f.write(video_bytes)

    return {"file_path": file_path, "downloaded": True}

