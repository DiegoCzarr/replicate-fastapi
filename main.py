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

# ----------------------------
#   CREATE VIDEO PREDICTION
# ----------------------------

@app.post("/generate")
async def generate_video(
    prompt: str = Form(...),
    aspect_ratio: str = Form("landscape"),
):
    # Monta o input SEM o campo "input_reference"
    model_input = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio
    }

    prediction = replicate.predictions.create(
        model="openai/sora-2",
        input=model_input
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }


# ----------------------------
#   POLLING
# ----------------------------
@app.get("/status/{prediction_id}")
async def prediction_status(prediction_id: str):
    prediction = replicate.predictions.get(prediction_id)

    output_url = prediction.output[0] if prediction.output else None

    return {
        "id": prediction.id,
        "status": prediction.status,
        "logs": prediction.logs,
        "output_url": output_url
    }

# ----------------------------
#   DOWNLOAD (opcional)
# ----------------------------
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
