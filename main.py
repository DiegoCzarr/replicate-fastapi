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
import random

load_dotenv()

app = FastAPI()

API_BASE_URL = "https://replicate-fastapi.onrender.com"

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
                f"Create a professional headshot of this {gender} subject in professional studio lighting, "
                f"wearing {attire_desc}, background is {background_desc}. "
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

            # Aqui pode ser que o replicate retorne URL ou binário,
            # verifique se precisa baixar ou já retorna link
            image_url = output if isinstance(output, str) else output[0]

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

