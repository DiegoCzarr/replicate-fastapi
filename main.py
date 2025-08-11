from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from itertools import product
import replicate
import os
import time
import shutil
from dotenv import load_dotenv
from uuid import uuid4
import json
import traceback

load_dotenv()

app = FastAPI()

API_BASE_URL = "https://replicate-fastapi.onrender.com"

# CORS (ajuste aqui para seu domínio Webflow)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajuste para ["https://jobodega.webflow.io"] em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cria pasta para arquivos temporários
os.makedirs("temp", exist_ok=True)
app.mount("/temp", StaticFiles(directory="temp"), name="temp")

def map_attire_description(attire, gender):
    attire = attire.lower()
    gender = gender.lower()
    if attire == "business professional":
        return "a suit and tie" if gender == "male" else "a professional corporate outfit"
    elif attire == "business casual":
        return "a suit with no tie" if gender == "male" else "a business casual outfit"     # Updated description
    elif attire == "casual":
        return "a t-shirt, a button-up shirt, a flannel, a sweater vest, or something currently trendy and fashionable"
    elif attire == "medical":
        return "modern medical attire, wearing a clean white lab coat over scrubs or business-casual medical clothing, with a stethoscope around their neck" # Removed unneeded description
    elif attire == "scientist":
        return "a white lab coat over casual-professional clothes, safety goggles on their head or eyes, and blue nitrile gloves"
    else:
        return attire

def map_background_description(background):
    background = background.lower()
    if background == "light gray":
        return "a neutral light grey professional studio photo background"     # Updated description
    elif background == "soft gradient":
        return "a soft gradient background"
    elif background == "corporate office":
        return "a bright and modern office with desks and computers in the background"
    elif background == "natural outdoors":
        return "an open space within a famous US National Park with natural daytime lighting"
    elif background == "trendy indoor space":
        return "a picturesque view of the inside of a world-famous tourist attraction"
    elif background == "startup office":
        return "a modern Bay-Area tech startup office"     # Updated description
    else:
        return background

@app.post("/gerar-headshot")
async def gerar_headshot(
    image: UploadFile = File(...),
    clothing: str = Form(...),       
    background: str = Form(...),     
    profession: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...)
):
    try:
        print(f"clothing raw value: {clothing}")
        print(f"background raw value: {background}")
        clothing_list = json.loads(clothing)
        background_list = json.loads(background)

        if not clothing_list or not background_list:
            return JSONResponse(status_code=400, content={"erro": "clothing ou background vazio."})

        file_ext = image.filename.split(".")[-1]
        img_id = str(uuid4())
        input_path = f"temp/{img_id}.{file_ext}"
        with open(input_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

        images = []
        combinations = list(product(clothing_list, background_list))

        for idx, (clothe, bg) in enumerate(combinations):
            attire_desc = map_attire_description(clothe, gender)
            background_desc = map_background_description(bg)

            prompt = (
                f"Create a professional headshot of this {gender} subject in professional studio lighting, "
                f"wearing {attire_desc} outfit, background is {background_desc}. "
                f"Maintain precise replication of subject's pose, head tilt, and eye line, "
                f"angle toward the camera, skin tone, and any jewelry."
            )

            print(f"🔹 Prompt {idx+1}: {prompt}")

            with open(input_path, "rb") as image_file:
                output = replicate.run(
                    "black-forest-labs/flux-kontext-pro",
                    input={
                        "prompt": prompt,
                        "input_image": image_file,
                        "output_format": "jpg"
                    }
                )

            output_path = f"temp/{img_id}_output_{idx+1}.jpg"
            with open(output_path, "wb") as f:
                f.write(output.read())

            image_url = f"{API_BASE_URL}/temp/{img_id}_output_{idx+1}.jpg"

            images.append({
                "url": image_url,
                "attire": clothe,
                "background": bg
            })

            time.sleep(0.3)

        return {"images": images}

    except Exception as e:
        print("❌ Erro:", str(e))
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"erro": str(e)})

