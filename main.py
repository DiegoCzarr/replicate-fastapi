from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from itertools import product
import replicate
from replicate import Client
from fastapi import Body
import os
import time
import shutil
from dotenv import load_dotenv
from uuid import uuid4
import json
import traceback
import random
import asyncio

load_dotenv()

app = FastAPI()

API_BASE_URL = "https://replicate-fastapi.onrender.com"

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not REPLICATE_API_TOKEN:
    raise RuntimeError("⚠️ Variável de ambiente REPLICATE_API_TOKEN não encontrada")

client = Client(api_token=REPLICATE_API_TOKEN)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajuste em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pasta temporária
os.makedirs("temp", exist_ok=True)
app.mount("/temp", StaticFiles(directory="temp"), name="temp")

# === MATRIZ DE ROUPAS ===
attire_matrix = {
    "Business Professional": {
        "man": ["dark suit with a {color} button-down shirt and tie"],
        "woman": ["{color} blouse with a dark suit"],
        "non-binary": ["dark suit with a {color} button-down shirt and tie"]
    },
    "Business Casual": {
        "man": ["dark suit with a {color} button-down shirt and no tie"],
        "woman": ["{color} silk blouse"],
        "non-binary": ["dark suit with a {color} button-down shirt and no tie"]
    },
    "Casual": {
        "man": [
            "{color} t-shirt",
            "{color} hoodie",
            "{color} flannel shirt",
            "{color} cardigan",
            "{color} turtleneck sweater",
            "denim jacket"
        ],
        "woman": [
            "{color} silk blouse",
            "{color} loose top with wide collar",
            "{color} flowy sundress",
            "{color} turtleneck sweater",
            "denim jacket"
        ],
        "non-binary": [
            "{color} t-shirt",
            "{color} hoodie",
            "{color} flannel shirt",
            "{color} cardigan",
            "{color} turtleneck sweater",
            "denim jacket"
        ]
    },
    "Doctor": {
        "unisex": ["white coat with stethoscope"]
    },
    "Clinician": {
        "man": ["{color} scrubs"],
        "woman": ["{color} scrubs"],
        "non-binary": ["{color} scrubs"]
    }
}

# === MATRIZ DE BACKGROUNDS ===
background_matrix = {
    "Light Gray": [
        "a neutral light grey professional studio photo background"
    ],
    "Soft Gradient": [
        "a soft white gradient background"
    ],
    "Corporate Office": [
        "a bright and modern corporate office overlooking the city"
    ],
    "Natural Outdoors": [
        "a picturesque view in front of snow-capped mountains with a clear blue sky",
        "a picturesque view in front of a golden hour sunlight over rolling hills.",
        "a picturesque view in front of a lush green park with a blurred city skyline.",
        "a picturesque view in front of ocean waves with soft pastel sunset.",
        "a picturesque view in front of vineyard rows with warm afternoon light.",
        "a picturesque view in front of cherry blossom trees in full bloom.",
        "a picturesque view in front of a rocky coastline with turquoise water.",
        "a picturesque view in front of a forest trail with dappled sunlight."
    ],
    "Trendy Indoor Space": [
        "a picturesque view of the inside of a modern office with glass walls and city view.",
        "a picturesque view of the inside of a cozy library with warm lighting and bookshelves.",
        "a picturesque view of the inside of an industrial loft with exposed brick and steel beams.",
        "a picturesque view of the inside of a minimalist studio with soft natural light.",
        "a picturesque view of the inside of a chic café with plants and wood accents.",
        "a picturesque view of the inside of a corporate boardroom with sleek design.",
        "a picturesque view of the inside of an art gallery with clean white walls.",
        "a picturesque view of the inside of a home office with stylish décor and greenery."
    ],
    "Startup Office": [
        "a modern Bay-Area tech startup office"
    ]
}

# === CORES ===
color_choices = {
    "Navy Blue": "#1A2B4C",
    "Charcoal Gray": "#36454F",
    "Black": "#000000",
    "White": "#FFFFFF",
    "Light Blue": "#ADD8E6",
    "Pale Gray": "#D3D3D3",
    "Beige": "#800020",
    "Burgundy": "#1A2B4C",
    "Emerald Green": "#50C878",
    "Soft Pink": "#F4C2C2"
}

def build_attire_description(attire, gender, color_name):
    attire = attire_matrix.get(attire, {})
    gender_key = gender.lower()
    options = attire.get(gender_key) or attire.get("unisex")
    if not options:
        raise ValueError(f"Nenhuma opção encontrada para {attire}/{gender}")
    choice = random.choice(options)
    return choice.replace("{color}", color_name)

def build_background_description(background):
    options = background_matrix.get(background)
    if not options:
        raise ValueError(f"Nenhuma opção encontrada para background {background}")
    return random.choice(options)

@app.post("/gerar-headshot")
async def gerar_headshot(
    image: UploadFile = File(...),
    clothing: str = Form(...),       # Lista JSON
    background: str = Form(...),     # Lista JSON
    profession: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    color: str = Form(None)          # Deixa opcional
):
    try:
        clothing_list = json.loads(clothing)
        background_list = json.loads(background)

        if not clothing_list or not background_list:
            return JSONResponse(status_code=400, content={"erro": "clothing ou background vazio."})

        # Se não foi enviada cor, define padrão
        if not color:
            color = "Black"

        if color not in color_choices:
            return JSONResponse(status_code=400, content={"erro": f"Cor '{color}' inválida."})

        file_ext = image.filename.split(".")[-1]
        img_id = str(uuid4())
        input_path = f"temp/{img_id}.{file_ext}"
        with open(input_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

        images = []
        combinations = list(product(clothing_list, background_list))

        for idx, (clothe, bg) in enumerate(combinations):
            # Passa o nome da cor (não o hex) para a descrição
            attire_desc = build_attire_description(clothe, gender, color)
            background_desc = build_background_description(bg)

            prompt = (
                f"Put this {gender} subject in professional studio lighting, "
                f"wearing {attire_desc}, background is {background_desc}. "
                f"Maintain precise replication of subject's pose, head tilt, and eye line, "
                f"angle toward the camera, skin tone, and any jewelry."
            )

            print(f"🔹 Prompt {idx+1}: {prompt}")

            with open(input_path, "rb") as image_file:
                prediction = client.predictions.create(
                    model="black-forest-labs/flux-kontext-pro",
                    input={
                        "prompt": prompt,
                        "input_image": image_file,
                        "output_format": "jpg"
                    }
                )
            
                # Polling até terminar
                while prediction.status not in ["succeeded", "failed", "canceled"]:
                    await asyncio.sleep(1)
                    prediction.reload()
            
                if prediction.status != "succeeded":
                    raise RuntimeError(f"Falha no Replicate: {prediction.status}")
            
                output = prediction.output
            
                # Tratamento seguro para diferentes formatos de retorno
                if isinstance(output, str):
                    image_url = output
                elif isinstance(output, list) and len(output) > 0:
                    image_url = output[0]
                elif hasattr(output, "url"):
                    image_url = output.url
                else:
                    raise ValueError(f"Formato de saída inesperado do replicate: {output}")
            
                images.append({
                    "url": image_url,
                    "attire": clothe,
                    "background": bg,
                    "color": color
                })
            
                time.sleep(0.3)


        return {"images": images}

    except Exception as e:
        print("❌ Erro:", str(e))
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"erro": str(e)})

@app.post("/editar-imagem")
async def editar_imagem(payload: dict = Body(...)):
    try:
        image_url = payload.get("image_url")
        edit_type = payload.get("edit_type")

        if not image_url or not edit_type:
            return JSONResponse(status_code=400, content={"erro": "Parâmetros inválidos"})

        # Define o prompt/transformação
        if edit_type == "remove-bg":
            prompt = "Remove the background of this image, keep only the subject."
        elif edit_type == "blur-bg":
            prompt = "Apply background blur, keep subject sharp."
        elif edit_type == "resize":
            prompt = "Resize this image to a square format, centered subject."
        else:
            return JSONResponse(status_code=400, content={"erro": "Tipo de edição inválido"})

        prediction = client.predictions.create(
            model="black-forest-labs/flux-kontext-pro",
            input={
                "prompt": prompt,
                "input_image": image_url,
                "output_format": "jpg"
            }
        )

        while prediction.status not in ["succeeded", "failed", "canceled"]:
            await asyncio.sleep(1)
            prediction.reload()

        if prediction.status != "succeeded":
            raise RuntimeError("Falha ao editar imagem")

        output = prediction.output
        if isinstance(output, str):
            edited_url = output
        elif isinstance(output, list) and len(output) > 0:
            edited_url = output[0]
        else:
            raise ValueError("Formato inesperado de saída")

        return {"image_url": edited_url}

    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})

