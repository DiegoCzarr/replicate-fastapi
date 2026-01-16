import os
import replicate
import requests
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api


load_dotenv()

# Guarda relação prediction_id -> cloudinary_public_id
FLUX_TEMP_IMAGES = {}
SORA2_TEMP_IMAGES = {}
SORA2_PRO_TEMP_IMAGES = {}
VEO3_TEMP_IMAGES = {}
SEEDREAM_TEMP_IMAGES = {}

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

    # Dropdowns
    aspect_ratio: str = Form("landscape"),
    seconds: str | None = Form(None),
    quality: str = Form("1080p"),

    # Imagem opcional
    reference_file: UploadFile | None = File(None),
):
    """
    Sora-2
    - Texto puro
    - Texto + imagem (via Cloudinary URL)
    """

    model_input = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": quality,
        
    }

    if seconds:
        model_input["seconds"] = int(seconds)

    cloudinary_public_id = None

    # 1️⃣ Upload temporário para Cloudinary (SE houver imagem)
    if reference_file:
        print("✅ Imagem recebida:", reference_file.filename)
        upload_result = cloudinary.uploader.upload(
            reference_file.file,
            folder="sora2-temp",
            resource_type="image"
        )

        image_url = upload_result["secure_url"]
        print("✅ CLOUDINARY URL:", image_url)
        cloudinary_public_id = upload_result["public_id"]

        # 2️⃣ Replicate recebe SOMENTE a URL
        model_input["input_reference"] = image_url
    else:
        print("⚠️ NO IMAGE RECEIVED")

    print("🚀 FINAL MODEL INPUT:", model_input)

    # 3️⃣ Criar prediction no Replicate
    prediction = replicate.predictions.create(
        model="openai/sora-2",
        input=model_input
    )

    # 4️⃣ Registrar imagem temporária para cleanup
    if cloudinary_public_id:
        SORA2_TEMP_IMAGES[prediction.id] = cloudinary_public_id

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }

from typing import List
import tempfile

# =====================================================
#               SORA 2 PRO - VIDEO
# =====================================================

from fastapi import Form, UploadFile, File
from typing import Optional

@app.post("/generate-sora-pro")
async def generate_sora_pro(
    prompt: str = Form(...),

    # dropdowns
    aspect_ratio: str = Form("landscape"),
    seconds: Optional[str] = Form(None),
    resolution: str = Form("standard"),

    # imagem opcional
    reference_file: Optional[UploadFile] = File(None)
):
    """
    Geração de vídeo com Sora-2 Pro
    - Texto puro
    - Texto + imagem (via Cloudinary URL)
    """

    # 🔹 input base
    model_input = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
    }

    if seconds:
        model_input["seconds"] = int(seconds)

    cloudinary_public_id = None

    # 🔹 Upload para Cloudinary se houver imagem
    if reference_file:
        print("✅ Imagem recebida:", reference_file.filename)

        upload_result = cloudinary.uploader.upload(
            reference_file.file,
            folder="sora2-pro-temp",
            resource_type="image"
        )

        image_url = upload_result["secure_url"]
        cloudinary_public_id = upload_result["public_id"]

        print("✅ CLOUDINARY URL:", image_url)

        model_input["input_reference"] = image_url
    else:
        print("⚠️ NO IMAGE RECEIVED")

    print("🚀 FINAL MODEL INPUT:", model_input)

    # 🔹 Criar prediction
    prediction = replicate.predictions.create(
        model="openai/sora-2-pro",
        input=model_input
    )

    # 🔹 Registrar imagem para cleanup
    if cloudinary_public_id:
        SORA2_TEMP_IMAGES[prediction.id] = cloudinary_public_id

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }



# =====================================================
#               KLING 2.5 PRO - VIDEO
# =====================================================

@app.post("/generate-kling-2.5-pro")
async def generate_kling_video(
    prompt: str = Form(...)
):
    """
    Kling v2.5 Turbo Pro
    - Text → Video
    """

    model_input = {
        "prompt": prompt
    }

    prediction = replicate.predictions.create(
        model="kwaivgi/kling-v2.5-turbo-pro",
        input=model_input
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }

# =====================================================
#               GEN 4 TURBO - VIDEO
# =====================================================

@app.post("/generate-gen4")
async def generate_gen4_video(
    prompt: str = Form(...),
    image: UploadFile = Form(...)
):
    """
    Runway Gen-4 Turbo
    - Image REQUIRED
    - Prompt REQUIRED
    """

    # Save image temporarily
    suffix = os.path.splitext(image.filename)[1] or ".png"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(await image.read())
    tmp.close()

    model_input = {
        "image": tmp.name,
        "prompt": prompt
    }

    prediction = replicate.predictions.create(
        model="runwayml/gen4-turbo",
        input=model_input
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }

# =====================================================
#                GOOGLE VEO 3.1 - VIDEO
# =====================================================

@app.post("/generate-veo")
async def generate_veo_video(
    prompt: str = Form(...),
    duration: int = Form(8),
    resolution: str = Form("1080p"),
    aspect_ratio: str = Form("16:9"),
    generate_audio: str = Form("true"),
    reference_images: Optional[List[UploadFile]] = File(None)
):
    """
    Geração de vídeo com Google Veo 3.1
    - Texto puro
    - Texto + múltiplas imagens
    """

    # -----------------------------
    # Parse generate_audio
    # -----------------------------
    generate_audio_bool = str(generate_audio).lower() in ["true", "1", "yes"]

    # -----------------------------
    # Upload reference images
    # -----------------------------
    reference_urls = []

    if reference_images:
        for img in reference_images:
            upload = cloudinary.uploader.upload(
                img.file,
                folder="veo3-temp",
                resource_type="image"
            )
            reference_urls.append(upload["secure_url"])

    # -----------------------------
    # Replicate input
    # -----------------------------
    model_input = {
        "prompt": prompt,
        "duration": int(duration),
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "generate_audio": generate_audio_bool,
    }

    if reference_urls:
        model_input["reference_images"] = reference_urls

    print("🚀 VEO 3.1 INPUT:", model_input)

    prediction = replicate.predictions.create(
        model="google/veo-3.1",
        input=model_input
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }


# =====================================================
#               GOOGLE VEO 3 FAST
# =====================================================

@app.post("/generate-veo-fast")
async def generate_veo_fast(
    prompt: str = Form(...),
    image: UploadFile = File(...),

    duration: int = Form(8),
    resolution: str = Form("720p"),
    aspect_ratio: str = Form("16:9"),
    generate_audio: bool = Form(True),
):
    """
    Google Veo 3 Fast
    - Image REQUIRED
    - Prompt REQUIRED
    """

    print("✅ Imagem recebida:", image.filename)

    upload_result = cloudinary.uploader.upload(
        image.file,
        folder="veo3-fast-temp",
        resource_type="image"
    )

    image_url = upload_result["secure_url"]
    public_id = upload_result["public_id"]

    print("✅ CLOUDINARY URL:", image_url)

    model_input = {
        "image": image_url,
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "generate_audio": generate_audio
    }

    print("🚀 FINAL MODEL INPUT:", model_input)

    prediction = replicate.predictions.create(
        model="google/veo-3-fast",
        input=model_input
    )

    VEO3_TEMP_IMAGES[prediction.id] = public_id

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

@app.post("/generate-nano-pro")
async def generate_nano_banana_pro(
    prompt: str = Form(...),
    aspect_ratio: str = Form("1:1"),
    output_format: str = Form("png")
):
    """
    Nano Banana Pro
    """

    model_input = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": output_format
    }

    prediction = replicate.predictions.create(
        model="google/nano-banana-pro",
        input=model_input
    )

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }

# =====================================================
#           SEEDREAM 4.5 - IMAGE
# =====================================================
@app.post("/generate-seedream-4.5")
async def generate_seedream(
    prompt: str = Form(...),
    size: str = Form("2K"),
    aspect_ratio: str = Form("16:9"),
    sequential_image_generation: str = Form("disabled"),
    input_images: List[UploadFile] = File(None)
):
    image_urls = []
    public_ids = []

    # 🔹 Upload opcional de imagens para Cloudinary
    print("📥 INPUT IMAGES:", input_images)
    if input_images:
        print("📥 QTD IMAGENS:", len(input_images))
        print("📥 NOMES:", [img.filename for img in input_images])
        for image in input_images[:12]:
            upload = cloudinary.uploader.upload(
                image.file,
                folder="seedream-temp",
                resource_type="image"
            )
            image_urls.append(upload["secure_url"])
            public_ids.append(upload["public_id"])

    prediction = replicate.predictions.create(
        model="bytedance/seedream-4.5",
        input={
            "prompt": prompt,
            "size": size,
            "aspect_ratio": aspect_ratio,
            "image_input": image_urls,  # ✅ CAMPO CORRETO
            "max_images": 1,
            "sequential_image_generation": sequential_image_generation
        }
    )

    SEEDREAM_TEMP_IMAGES[prediction.id] = public_ids

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }
# =====================================================
#        FLUX KONTEXT MAX - IMAGE + TEXT
# =====================================================

@app.post("/generate-flux-kontext")
async def generate_flux_kontext(
    prompt: str = Form(...),
    output_format: str = Form("jpg"),
    input_image: UploadFile = File(...)
):
    """
    Flux Kontext Max
    Texto + imagem obrigatória
    """

    # 1️⃣ Upload temporário para Cloudinary
    upload_result = cloudinary.uploader.upload(
        input_image.file,
        folder="flux-kontext-temp",
        resource_type="image"
    )

    image_url = upload_result["secure_url"]
    public_id = upload_result["public_id"]

    # 2️⃣ Criar prediction no Replicate (SOMENTE URL)
    prediction = replicate.predictions.create(
        model="black-forest-labs/flux-kontext-max",
        input={
            "prompt": prompt,
            "input_image": image_url,
            "output_format": output_format
        }
    )

    # 3️⃣ Registrar imagem temporária para cleanup depois
    FLUX_TEMP_IMAGES[prediction.id] = public_id

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }


# =====================================================
#               FLUX 2 PRO - IMAGE
# =====================================================

@app.post("/generate-flux-2-pro")
async def generate_flux_2_pro(
    prompt: str = Form(...),

    resolution: str = Form("1 MP"),
    aspect_ratio: str = Form("1:1"),
    output_format: str = Form("webp"),
    output_quality: int = Form(80),
    safety_tolerance: int = Form(2),

    input_images: Optional[List[UploadFile]] = File(None)
):
    """
    Flux 2 Pro
    - Texto puro
    - Texto + imagens de referência
    """

    reference_urls = []
    public_ids = []

    # 🔹 Upload opcional das imagens
    if input_images:
        for img in input_images:
            upload = cloudinary.uploader.upload(
                img.file,
                folder="flux-2-pro-temp",
                resource_type="image"
            )
            reference_urls.append(upload["secure_url"])
            public_ids.append(upload["public_id"])

    # 🔹 Input FINAL do modelo
    model_input = {
        "prompt": prompt,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "output_format": output_format,
        "output_quality": output_quality,
        "safety_tolerance": safety_tolerance,
        "input_images": reference_urls
    }

    print("🚀 FLUX 2 PRO INPUT:", model_input)

    prediction = replicate.predictions.create(
        model="black-forest-labs/flux-2-pro",
        input=model_input
    )

    # opcional: guardar IDs pra cleanup
    FLUX_TEMP_IMAGES[prediction.id] = public_ids

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }


# =====================================================
#              FLUX 1.1 PRO - IMAGE
# =====================================================

@app.post("/generate-flux")
async def generate_flux(
    prompt: str = Form(...),
    prompt_upsampling: bool = Form(False)
):
    prediction = replicate.predictions.create(
        model="black-forest-labs/flux-1.1-pro",
        input={
            "prompt": prompt,
            "prompt_upsampling": prompt_upsampling
        }
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

        # 🔥 Cleanup Cloudinary quando finalizar
    if prediction.status in ["succeeded", "failed"]:
        public_id = (
            FLUX_TEMP_IMAGES.pop(prediction_id, None)
            or SORA2_TEMP_IMAGES.pop(prediction_id, None)
            or SORA2_PRO_TEMP_IMAGES.pop(prediction_id, None)
            or VEO3_TEMP_IMAGES.pop(prediction_id, None)
            or SEEDREAM_TEMP_IMAGES.pop(prediction_id, None)
        )


        if public_id:
            try:
                cloudinary.uploader.destroy(public_id)
                print(f"[CLOUDINARY] Deleted temp image: {public_id}")
            except Exception as e:
                print(f"[CLOUDINARY ERROR] {e}")


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
