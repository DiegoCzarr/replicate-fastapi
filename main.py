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
        "a realistic view inside a modern café with exposed brick, modern furniture, warm lighting, and a counter with baked goods on display.",
        "a picturesque view inside a cozy, artisanal cafe with vintage wooden tables, soft natural light streaming through a window, and a display of freshly roasted coffee beans or unique pastries softly blurred in the background.",
        "a picturesque view inside a contemporary minimalist cafe with clean lines, industrial concrete elements, and a single, strategically placed modern art piece on a wall softly blurred in the background."
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
        "a dark navy professional studio background",
        "a light professional studio background with a pattern.",
        "a dark professional studio background with a pattern."
    ],

      "soft-lighting": [
        "a soft white gradient background.",
        "a soft off-white gradient background.",
        "a soft light gray gradient background.",
        "a soft dark gray gradient background.",
        "a soft light blue gradient background."
      ],
    
      "modern-office": [
        "a picturesque view of the inside a bright and modern corporate high-rise office overlooking the city.",
        "a picturesque view of the inside of a corporate boardroom with sleek design.",
        "a picturesque view of the inside of a modern office with glass walls and city view.",
        "a realistic view of a an office floor with open cubicles.",
        "a realistic view of an office floor with open cubicles.",
        "a picturesque view of the inside of a creative workspace with whiteboard, sticky notes, and open layout softly blurred"
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
        "a picturesque view of a hawaiian beach with natural trees and plants.",
        "a picturesque view of a rugged, windswept coastline with dramatic rock formations, crashing white-capped waves, and sparse, hardy coastal vegetation.",
        "a picturesque view of a calm, secluded beach cove with smooth pebbles, crystal-clear shallow water, and dense green foliage on the cliffs above softly blurred in the background."
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
        "a picturesque view of the inside of a minimalist studio with soft natural light.",
        "a picturesque view of the inside of a luxury hotel lobby interior with marble flooring and ambient golden lighting.",
        "a picturesque view of the inside of a modern penthouse apartment with panoramic windows and city view blurred behind."
      ],
    
      "restaurant": [
        "a picturesque view inside of a fine dining establishment with cozy lighting and clean, modern furniture, with a large window opening out to a view below.",
        "a picturesque view inside of a trendy fusion bar and restaurant that is naturally lit, with modern fixtures and lighting.",
        "a picturesque view inside the dining area of a clean and hyper modern contemporary restaurant with a long horizontal window that shows a peek inside the kitchen.",
        "a picturesque view inside of a high-end restaurant with moody lighting, warm wood tones, and plush seating softly out of focus",
        "a picturesque view inside of a coastal restaurant with large windows, beach view, and breezy neutral tones."
      ],
    
      "museum": [
        "a picturesque view of the inside a world famous museum with artwork in the background",
        "a picturesque view of the inside of an art gallery with clean white walls.",
        "a realistic view of a contemporary art museum, with a series of stainless steel avant garde sculptures on display.",
        "a picturesque view inside of a modern art gallery with concrete floors, bright ceiling lights, and colorful modern art installations",
        "a picturesque view inside of a natural history museum with dinosaur skeletons and dramatic spotlighting blurred in background"
      ],
    
      "legal-office": [
        "a picturesque view of the inside a legal office with legal books on a shelf blurred in the background.",
        "a realistic view of a small, modern office meeting room, enclosed by glass walls, surrounded by bookshelves with legal books.",
        "a picturesque view of the inside of an old-world legal chamber with heavy wood furniture, soft yellow lighting, and a subtle vignette",
        "a picturesque view of the inside of a traditional law office interior with dark mahogany furniture, green banker’s lamp, and rows of old law books.",
        "a picturesque view of the inside of an elegant vintage study with wood paneling, leather chairs, and stacks of legal volumes softly blurred."
      ],
    
      "library": [
        "a picturesque view of the inside of a cozy library with warm lighting and bookshelves.",
        "a realistic view of a modern library, with a window for natural lighting and warm interior lighting and shelves of books, and a small seating area for readers.",
        "a realistic view of softly blurred corner of a library featuring a classic leather armchair, a small side table, and shelves of books that conveys a cozy, intellectual atmosphere.",
        "a picturesque view of the inside of a university study hall with high ceilings, rows of bookshelves, and warm afternoon light",
        "a picturesque view of the inside of an old library interior with dust particles in sunlight, creating a timeless academic mood."
      ],
    
      "medical": [
        "a picturesque view of the inside of a clean and modern medical research setting, with lab equipment blurred in the background.",
        "a modern hospital setting with an admitting desk and waiting room, with contemporary furniture.",
        "a picturesque view of the inside of a modern hospital setting with an admitting desk and waiting room, with contemporary furniture.",
        "a picturesque view of the inside of a professional consultation room with anatomical charts and a tidy white countertop.",
        "a picturesque view of the inside of a pediatric office with friendly decor, bright colors, and welcoming atmosphere.",
        "a picturesque view of an atrium of a modern research hospital."
      ],
    
      "gym": [
        "a picturesque view of the inside of a classic gym studio, with workout equipment blurred in the background.",
        "a picturesque view of the inside of a pilates classroom with equipment blurred in the background.",
        "a picturesque view of the inside of a yoga studio.",
        "a picturesque view of an open air fitness studio, with plyometric workout equipment in the background.",
        "a picturesque view of the inside of a Crossfit gym with people working out in the background."
      ],
    
      "construction": [
        "a picturesque view of the inside of an outdoors construction site with equipment blurred in the background",
        "a picturesque view of the inside of an industrial facility with equipment blurred in the background",
        "a picturesque view of an architectural blueprint station on a construction site, with rolled plans and a hard hat subtly blurred on a temporary table in the background, emphasizing planning and design.",
        "a picturesque view of the inside of an industrial facility with equipment blurred in the background",
        "a picturesque view of a high-rise construction site from an elevated perspective, showing a city skyline in the distant, soft focus, and scaffolding or structural elements up close but blurred in the background."
      ],
    
      "classroom": [
        "a picturesque view of the inside of a grade school classroom with desks and a whiteboard blurred in the background",
        "a picturesque view of the inside of a high school class room with desks and maps on the wall",
        "a realistic view inside of a university lecture hall with cozy lighting.",
        "a picturesque view inside of a university science department lab with whiteboards covered in equations, stacked scientific journals, and a model of an atom or DNA helix softly blurred in the background.",
        "a picturesque view inside of a STEM-focused classroom with lab tables, laptops, and whiteboards softly out of focus."
      ],
    
      "real-estate": [
        "a picturesque view of a suburban neighborhood with houses blurred in the background.",
        "a picturesque view of a house with a “Sold” sign in front.",
        "a modern, airy dining room with natural lighting, and a large island and kitchen softly blurred in the background.",
        "a picturesque view of a luxury open-concept home interior with marble floors, pendant lighting, and panoramic glass walls.",
        "a picturesque view of a luxury home exterior with blurred “For Sale” sign, manicured lawn, and blue-sky background."
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
        "a picturesque view of the inside of a modern home office with tidy desk setup, neutral walls, and natural light from a nearby window",
        "a picturesque view of the inside of a contemporary home office set up in a small nook. Include bookshelves, a keyboard, monitor, and a Herman Miller chair.",
        "a picturesque view of the inside of a home office set up inside an upstairs loft. Include houseplants, bookshelves, and a desk and monitor. Include contemporary furnishings."
      ],
    
      "science-lab": [
        "a picturesque view of the inside of a bright modern laboratory, shelves of glass beakers and microscopes in soft focus behind them.",
        "a picturesque view of the inside of a clean white laboratory background with test tubes, lab coats, and scientific equipment slightly blurred.",
        "a realistic view of the inside of a clean biotech laboratory background with test equipment, computers, and a working counter.",
        "a picturesque view of the inside of a high-tech physics laboratory with complex electronic equipment, suggesting advanced research.",
        "a picturesque view of the inside of an environmental science lab with soil samples, water testing kits, and charts or maps softly blurred on a workbench in the background, suggesting a focus on nature and data."
      ]
}

# === CORES ===
color_choices = {
    "navy": "#1A2B4C",
    "charcoal": "#36454F",
    "gray": "D3D3D3",
    "black": "#000000",
    "white": "#FFFFFF",
    "blue": "#ADD8E6",
    "tan": "#C3B091",
    "beige": "#800020",
    "burgundy": "#1A2B4C",
    "emerald Green": "#50C878",
    "soft pink": "#F4C2C2"
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
    clothing: str = Form(...),       # Lista JSON (string)
    background: str = Form(...),     # Lista JSON (string)
    gender: str = Form(...),
    color: str = Form(None)          # Deixa opcional
):
    try:
        clothing_value = clothing.strip()
        background_list = json.loads(background)

        if not clothing_value or not background_list:
            return JSONResponse(status_code=400, content={"erro": "clothing ou background vazio."})

        # Define cor padrão se não enviada
        if not color:
            color = "Black"

        if color not in color_choices:
            return JSONResponse(status_code=400, content={"erro": f"Cor '{color}' inválida."})

        # salva arquivo recebido
        file_ext = image.filename.split(".")[-1]
        img_id = str(uuid4())
        input_path = f"temp/{img_id}.{file_ext}"
        with open(input_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

        images = []
        MODEL_ID = "black-forest-labs/flux-kontext-pro"

        # Para cada background selecionado, gerar exatamente 5 imagens
        for bg in background_list:
            bg_key = bg  # assumimos bg corresponde a chave do background_matrix
            variations = background_matrix.get(bg_key, [bg_key])

            # Se houver >=5 variações, escolhe 5 aleatórias sem repetição
            # Se houver <5, embaralha e repete até completar 5 (mantendo alguma variabilidade)
            chosen_variations = []
            if len(variations) >= 5:
                # sample sem repetição
                chosen_variations = random.sample(variations, 5)
            else:
                # preencha repetindo/embaralhando até ter 5
                pool = variations.copy()
                while len(chosen_variations) < 5:
                    random.shuffle(pool)
                    for v in pool:
                        if len(chosen_variations) >= 5:
                            break
                        chosen_variations.append(v)
                # garante exatamente 5
                chosen_variations = chosen_variations[:5]

            # Gera uma imagem para cada variação escolhida (5 por background)
            for idx, variation in enumerate(chosen_variations):
                attire_desc = build_attire_description(clothing_value, gender, color)
                background_desc = variation  # já é a string descritiva do background

                prompt = (
                    f"Put this {gender} subject in professional studio lighting, "
                    f"wearing {attire_desc}, background is {background_desc}. "
                    f"Maintain precise replication of subject's pose, head tilt, and eye line, "
                    f"angle toward the camera, skin tone, and any jewelry."
                )

                print(f"🔹 Generating for background '{bg}' (variation {idx+1}/5): {background_desc}")
                with open(input_path, "rb") as image_file:
                    prediction = client.predictions.create(
                        model=MODEL_ID,
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
                        # registra e avança (ou, se preferir, pode abortar tudo)
                        print(f"⚠️ Prediction status for bg={bg}, var='{variation}': {prediction.status}")
                        # opcional: adicionar objeto com erro
                        images.append({
                            "url": None,
                            "attire": clothing_value,
                            "background": bg,
                            "variation": variation,
                            "color": color,
                            "status": prediction.status
                        })
                        continue

                    output = prediction.output

                    # normaliza formato de saída como antes
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
                        "attire": clothing_value,
                        "background": bg,
                        "variation": variation,
                        "color": color,
                        "status": "succeeded"
                    })

                # pequeno delay para não sobrecarregar (opcional)
                time.sleep(0.2)

        # limpa arquivo temporário
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except Exception:
            pass

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

