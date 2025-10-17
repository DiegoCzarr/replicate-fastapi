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

OPTIONS = {
    "doctor": {
        "clothes": ["Jaleco", "Scrub"],
        "colors": ["Branco", "Azul", "Verde Hospitalar"],
        "backgrounds": ["Clínica", "Escritório Médico", "Hospital"]
    },
    "engineer": {
        "clothes": ["Capacete", "Colete de Segurança", "Camisa Polo"],
        "colors": ["Laranja", "Azul", "Cinza"],
        "backgrounds": ["Obra", "Escritório Corporativo", "Laboratório"]
    },
    "headshot": {
        "clothes": ["Terno", "Blazer", "Camisa Social"],
        "colors": ["Preto", "Cinza", "Azul Marinho"],
        "backgrounds": ["Neutro", "Escritório Moderno", "Biblioteca"]
    }
}

@app.get("/options")
def get_options(photo_type: str):
    return OPTIONS.get(photo_type, {})
# === MATRIZ DE ROUPAS ===
attire_matrix = {
    "Business Professional": {
        "man": ["dark suit with a {color} button-down shirt and tie"],
        "woman": ["{color} blouse with a dark suit"],
        "non-binary": ["dark suit with a {color} button-down shirt and tie"]
    },
    "business-casual": {
        "man": ["dark suit with a {color} button-down shirt and no tie"],
        "woman": ["{color} silk blouse"],
        "non-binary": ["dark suit with a {color} button-down shirt and no tie"]
    },
    "casual": {
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
    "light-gray": [
        "a neutral light grey professional studio photo background"
    ],
    "soft-gradient": [
        "a soft white gradient background"
    ],
    "corporate-office": [
        "a bright and modern corporate office overlooking the city"
    ],

    "cafe": [
        "a picturesque view inside of a chic café with plants and wood accents.",
        "a picturesque view inside a Parisian café with a counter with baked goods on display, tables and chairs, and view of the city outside the windows.",
        "a realistic view inside a modern café with exposed brick, modern furniture, warm lighting, and a counter with baked goods on display."
    ],

    "natural-outdoors": [
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
    ],

    "studio": [
        "a neutral light grey professional studio photo background",
        "a dark gray professional studio photo background",
        "a dark navy professional studio background"
    ],

      "soft-lighting": [
        "a soft white gradient background."
      ],
    
      "modern-office": [
        "a picturesque view of the inside a bright and modern corporate high-rise office overlooking the city.",
        "a picturesque view of the inside of a corporate boardroom with sleek design.",
        "a picturesque view of the inside of a modern office with glass walls and city view.",
        "a realistic view of a an office floor with open cubicles."
      ],
    
      "urban": [
        "a picturesque view in front of a lush green park with a blurred city skyline.",
        "a picturesque view on a highrise rooftop with modern furniture and a metropolitan skyline.",
        "a picturesque view in an metropolitan modern plaza, surrounded by buildings with glass facades, and shadows from tall towers.",
        "a realistic view of a rooftop bar overlooking a glowing cityscape, blurred traffic trails below, glowing skyline beyond.",
        "a realistic New York City skyline view from Brooklyn, bridges, glowing skyscrapers, and water reflections in warm sunlight.",
        "a picturesque view of a European cobblestone street lined with old brick apartments, scooters parked outside, warm sunset glow.",
        "a realistic view of a bustling street in Paris in afternoon light."
      ],
    
      "beach": [
        "a picturesque view in front of ocean waves with soft pastel sunset.",
        "a picturesque view in front of a rocky coastline with tidepools by the water.",
        "a picturesque view of a hawaiian beach with natural trees and plants."
      ],
    
      "nature": [
        "a picturesque view in front of a famous national park landmark",
        "a picturesque view in front of a forest trail with dappled sunlight.",
        "a picturesque view in front of snow-capped mountains with a clear blue sky.",
        "a picturesque view in front of a golden hour sunlight over rolling hills.",
        "a picturesque view in front of vineyard rows with warm afternoon light.",
        "a vibrant, softly blurred background brimming with a variety of colorful flowers and rich green foliage."
      ],
    
      "indoors": [
        "a picturesque view of the inside of an industrial loft with exposed brick and steel beams.",
        "a picturesque view of the inside of a minimalist studio with soft natural light."
      ],
    
      "restaurant": [
        "a picturesque view inside of a fine dining establishment with cozy lighting and clean, modern furniture, with a large window opening out to a view below.",
        "a picturesque view inside of a trendy fusion bar and restaurant that is naturally lit, with modern fixtures and lighting.",
        "a picturesque view inside the dining area of a clean and hyper modern contemporary restaurant with a long horizontal window that shows a peek inside the kitchen."
      ],
    
      "museum": [
        "a picturesque view of the inside a world famous museum with artwork in the background",
        "a picturesque view of the inside of an art gallery with clean white walls.",
        "a realistic view of a contemporary art museum, with a series of stainless steel avant garde sculptures on display."
      ],
    
      "legal-office": [
        "a picturesque view of the inside a legal office with legal books on a shelf blurred in the background.",
        "a realistic view of a small, modern office meeting room, enclosed by glass walls, surrounded by bookshelves with legal books."
      ],
    
      "library": [
        "a picturesque view of the inside of a cozy library with warm lighting and bookshelves.",
        "a realistic view of a modern library, with a window for natural lighting and warm interior lighting and shelves of books, and a small seating area for readers.",
        "a realistic view of softly blurred corner of a library featuring a classic leather armchair, a small side table, and shelves of books that conveys a cozy, intellectual atmosphere."
      ],
    
      "cafe": [
        "a picturesque view inside of a chic café with plants and wood accents.",
        "a picturesque view inside a Parisian café with a counter with baked goods on display, tables and chairs, and view of the city outside the windows.",
        "a realistic view inside a modern café with exposed brick, modern furniture, warm lighting, and a counter with baked goods on display."
      ],
    
      "medical": [
        "a picturesque view of the inside of a clean and modern medical research setting, with lab equipment blurred in the background.",
        "a modern hospital setting with an admitting desk and waiting room, with contemporary furniture."
      ],
    
      "gym": [
        "a picturesque view of the inside of a classic gym studio, with workout equipment blurred in the background.",
        "a picturesque view of the inside of a pilates classroom with equipment blurred in the background.",
        "a picturesque view of the inside of a yoga studio.",
        "a picturesque view of an open air fitness studio, with plyometric workout equipment in the background."
      ],
    
      "construction": [
        "a picturesque view of the inside of an outdoors construction site with equipment blurred in the background",
        "a picturesque view of the inside of an industrial facility with equipment blurred in the background"
      ],
    
      "classroom": [
        "a picturesque view of the inside of a grade school classroom with desks and a whiteboard blurred in the background",
        "a picturesque view of the inside of a high school class room with desks and maps on the wall",
        "a realistic view inside of a university lecture hall with cozy lighting."
      ],
    
      "real-estate": [
        "a picturesque view of a suburban neighborhood with houses blurred in the background.",
        "a picturesque view of a house with a “Sold” sign in front.",
        "a modern, airy dining room with natural lighting, and a large island and kitchen softly blurred in the background."
      ],
    
      "music-studio": [
        "a picturesque view of the inside of a music studio with equipment blurred in the background",
        "a picturesque view of the inside of a recording studio with equipment blurred in the background",
        "a picturesque view of the inside of a music classroom with equipment blurred in the background",
        "a picturesque view of the inside of a musical theater with equipment blurred in the background",
        "a picturesque view of the inside of a small music venue with a stage, lighting, and instruments in the background."
      ],
    
      "home-office": [
        "a picturesque view of the inside of a home office with stylish décor and greenery.",
        "a picturesque view of the inside of a clean home office with bookshelves, a desk, and a computer monitor softly blurred in the background.",
        "a picturesque view of the inside of a modern home office with tidy desk setup, neutral walls, and natural light from a nearby window"
      ],
    
      "science-lab": [
        "a picturesque view of the inside of a bright modern laboratory, shelves of glass beakers and microscopes in soft focus behind them.",
        "a picturesque view of the inside of a clean white laboratory background with test tubes, lab coats, and scientific equipment slightly blurred.",
        "a realistic view of the inside of a clean biotech laboratory background with test equipment, computers, and a working counter."
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
    clothing: str = Form(...),
    background: str = Form(...),
    gender: str = Form(...),
    color: str = Form(None)
):
    try:
        clothing_value = clothing.strip()
        background_list = json.loads(background)

        if not clothing_value or not background_list:
            return JSONResponse(status_code=400, content={"erro": "clothing ou background vazio."})

        if not color:
            color = "Black"

        if color not in color_choices:
            return JSONResponse(status_code=400, content={"erro": f"Cor '{color}' inválida."})

        file_ext = image.filename.split(".")[-1]
        img_id = str(uuid4())
        input_path = f"temp/{img_id}.{file_ext}"
        with open(input_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

        # === NOVO: Dicionário de resultados categorizados ===
        categorized_results = {}

        # === Para cada background selecionado ===
        for bg in background_list:
            background_options = background_matrix.get(bg)
            if not background_options:
                print(f"⚠️ Nenhuma descrição encontrada para background: {bg}")
                continue

            # Garante no máximo 5 descrições únicas (ou repete se tiver menos)
            descriptions = (
                random.sample(background_options, min(5, len(background_options)))
                if len(background_options) >= 5
                else [random.choice(background_options) for _ in range(5)]
            )

            categorized_results[bg] = []

            # === Gera 5 imagens para este background ===
            for desc_idx, bg_description in enumerate(descriptions):
                attire_desc = build_attire_description(clothing_value, gender, color)

                prompt = (
                    f"Professional {gender} portrait photo, wearing {attire_desc}, "
                    f"background is {bg_description}. Maintain exact likeness, pose, lighting, "
                    f"and facial features. Professional headshot style, 8k detail, studio lighting."
                )

                print(f"🔹 [{bg}] Prompt {desc_idx+1}: {prompt}")

                with open(input_path, "rb") as image_file:
                    prediction = client.predictions.create(
                        model="black-forest-labs/flux-kontext-pro",
                        input={
                            "prompt": prompt,
                            "input_image": image_file,
                            "output_format": "jpg"
                        }
                    )

                # Polling até finalizar
                while prediction.status not in ["succeeded", "failed", "canceled"]:
                    await asyncio.sleep(1)
                    prediction.reload()

                if prediction.status != "succeeded":
                    print(f"❌ Falha no background {bg} ({desc_idx+1}): {prediction.status}")
                    continue

                output = prediction.output
                if isinstance(output, str):
                    image_url = output
                elif isinstance(output, list) and len(output) > 0:
                    image_url = output[0]
                elif hasattr(output, "url"):
                    image_url = output.url
                else:
                    raise ValueError(f"Formato inesperado de saída: {output}")

                categorized_results[bg].append({
                    "url": image_url,
                    "attire": clothing_value,
                    "color": color,
                    "background_description": bg_description
                })

                await asyncio.sleep(0.3)  # evita rate-limit

        return {"results": categorized_results}

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
            prompt = "Apply white background, keep only the subject."
        elif edit_type == "blur-bg":
            prompt = "Apply background blur, keep subject sharp."
        elif edit_type == "resize":
            prompt = "Resize this image to a 4:3 format, centered subject."
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

