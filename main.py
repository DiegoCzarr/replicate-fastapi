import os
import replicate
import requests
from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# Auth
os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPLICATE_API_TOKEN")

app = FastAPI()

origins = [
    "https://jobodega.webflow.io",
    "https://www.jobodega.com",
    "http://localhost:3000",
    "*",  # (opcional durante testes)
]

# Allow Webflow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,   # coloque seu domínio Webflow se quiser limitar
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
#   CREATE VIDEO PREDICTION
# ----------------------------
@app.post("/generate")
async def generate_video(
    prompt: str = Form(...),
    aspect_ratio: str = Form("landscape"),
    reference_file: UploadFile | None = None
):
    """
    Cria a prediction no Replicate e retorna o prediction_id para o Webflow.
    Seu front irá fazer polling depois.
    """

    input_reference = None

    # Se o usuário enviou arquivo
    if reference_file:
        input_reference = reference_file.file  # o client do Replicate faz upload automático

    prediction = replicate.predictions.create(
        model="openai/sora-2",
        input={
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "input_reference": input_reference
        }
    )

    return {"prediction_id": prediction.id, "status": prediction.status}


# ----------------------------
#   POLLING
# ----------------------------
@app.get("/status/{prediction_id}")
async def prediction_status(prediction_id: str):
    """
    Consulta o status da prediction.
    """

    prediction = replicate.predictions.get(prediction_id)

    # Quando finalizar, prediction.output é uma lista com URLs
    output_url = None
    if prediction.output and len(prediction.output) > 0:
        output_url = prediction.output[0]

    return {
        "id": prediction.id,
        "status": prediction.status,
        "logs": prediction.logs,
        "output_url": output_url
    }


# ----------------------------
#   DOWNLOAD FINAL (opcional)
# ----------------------------
@app.get("/download/{prediction_id}")
async def download_prediction(prediction_id: str):
    """
    Baixa o vídeo do Replicate e salva localmente (opcional).
    """

    prediction = replicate.predictions.get(prediction_id)

    if not prediction.output:
        return {"error": "Output ainda não está pronto."}

    output_url = prediction.output[0]

    video_bytes = requests.get(output_url).content

    file_path = f"output_{prediction_id}.mp4"
    with open(file_path, "wb") as f:
        f.write(video_bytes)

    return {"file_path": file_path, "downloaded": True}
