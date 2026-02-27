import os
import replicate
import requests
from datetime import datetime
from fastapi import FastAPI, UploadFile, Form, File, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
import hmac
import hashlib

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# =========================================
# MODELS
# =========================================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    memberstack_id = Column(String, unique=True)
    email = Column(String)
    credits = Column(Integer, default=50)

class Creation(Base):
    __tablename__ = "creations"
    id = Column(Integer, primary_key=True)
    memberstack_id = Column(String)
    prompt = Column(Text)
    model = Column(String)
    result_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# =========================================
# CLOUDINARY
# =========================================
cloudinary.config(secure=True)

load_dotenv()

# Guarda relação prediction_id -> cloudinary_public_id
FLUX_TEMP_IMAGES = {}
SORA2_TEMP_IMAGES = {}
SORA2_PRO_TEMP_IMAGES = {}
VEO3_TEMP_IMAGES = {}
SEEDREAM_TEMP_IMAGES = {}
NANOBANANA_TEMP_IMAGES = {}
KLING_TEMP_IMAGES = {}
GEN4_TEMP_IMAGES = {}

# Auth
os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPLICATE_API_TOKEN")

app = FastAPI()
PREDICTION_META = {}

def get_user(db, member_id):
    user = db.query(User).filter(User.memberstack_id == member_id).first()
    if not user:
        user = User(memberstack_id=member_id, credits=50)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

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
    prompt: str = Form(...),
    aspect_ratio: str = Form("16:9"),
    duration: int = Form(5),

    first_frame: Optional[UploadFile] = File(None),
    last_frame: Optional[UploadFile] = File(None),
):
    """
    Kling v2.5 Turbo Pro
    - Text → Video
    """

    model_input = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "duration": duration
    }

    cloudinary_public_id = None

    # 🔹 Upload para Cloudinary se houver imagem
    if first_frame:
        upload = cloudinary.uploader.upload(
            first_frame.file,
            folder="kling-temp",
            resource_type="image"
        )
        model_input["first_frame"] = upload["secure_url"]
    
    if last_frame:
        upload = cloudinary.uploader.upload(
            last_frame.file,
            folder="kling-temp",
            resource_type="image"
        )
        model_input["last_frame"] = upload["secure_url"]

    else:
        print("⚠️ NO IMAGE RECEIVED")

    print("🚀 FINAL MODEL INPUT:", model_input)

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
    duration: int = Form(5),
    aspect_ratio: str = Form("16:9"),
    
    reference_file: Optional[UploadFile] = File(None)
):
    """
    Runway Gen-4 Turbo
    - Image REQUIRED
    - Prompt REQUIRED
    """
    model_input = {
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio
    }

    cloudinary_public_id = None

    # 🔹 Upload para Cloudinary se houver imagem
    if reference_file:
        print("✅ Imagem recebida:", reference_file.filename)

        upload_result = cloudinary.uploader.upload(
            reference_file.file,
            folder="gen4-temp",
            resource_type="image"
        )

        image_url = upload_result["secure_url"]
        cloudinary_public_id = upload_result["public_id"]

        print("✅ CLOUDINARY URL:", image_url)

        model_input["image"] = image_url
    else:
        print("⚠️ NO IMAGE RECEIVED")

    print("🚀 FINAL MODEL INPUT:", model_input)
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
    member_id: str = Form(...),
    aspect_ratio: str = Form("16:9"),
    input_images: List[UploadFile] = File(None)
):
    db = SessionLocal()
    user = get_user(db, member_id)

    if user.credits <= 0:
        db.close()
        return JSONResponse(status_code=403, content={"error": "Créditos insuficientes."})
    
    image_urls = []
    public_ids = []

    # 🔹 Upload opcional de imagens
    image_urls = []
    if input_images:
        print("📥 QTD IMAGENS:", len(input_images))
        print("📥 NOMES:", [img.filename for img in input_images])

        for image in input_images:
            
            #upload = cloudinary.uploader.upload(
                #image.file,
                #folder="nanobanana-temp",
                #resource_type="image"
            #)
            upload = cloudinary.uploader.upload(await image.read(), folder="nanobanana-temp", resource_type="image")

            image_urls.append(upload["secure_url"])
            public_ids.append(upload["public_id"])

    print("✅ URLs enviadas ao modelo:", image_urls)

    model_input = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "image_input": image_urls  # se houver imagens
    }

    prediction = replicate.predictions.create(
        model="google/nano-banana",
        input=model_input
    )
    
    user.credits -= 1
    db.commit()
    db.close()

    PREDICTION_META[prediction.id] = {
        "member_id": member_id,
        "prompt": prompt,
        "model": "flux-kontext-pro"
    }

    # 🔹 Salva imagens temporárias para limpeza futura
    NANOBANANA_TEMP_IMAGES[prediction.id] = public_ids

    return {
        "prediction_id": prediction.id,
        "status": prediction.status
    }

@app.post("/generate-nano-pro")
async def generate_nano_banana_pro(
    prompt: str = Form(...),
    aspect_ratio: str = Form("1:1"),
    output_format: str = Form("png"),
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

    len(image_urls) if image_urls else 0,

    """
    Nano Banana Pro
    """

    model_input = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": output_format,
        "image_input": image_urls,  # ✅ CAMPO CORRETO
    }

    prediction = replicate.predictions.create(
        model="google/nano-banana-pro",
        input=model_input
    )
    
    NANOBANANA_TEMP_IMAGES[prediction.id] = public_ids
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

    len(image_urls) if image_urls else 0,

    max_images = 1
    prediction = replicate.predictions.create(
        model="bytedance/seedream-4.5",
        input={
            "prompt": prompt,
            "size": size,
            "aspect_ratio": aspect_ratio,
            "image_input": image_urls if image_urls else None,  # ✅ CAMPO CORRETO
            "max_images": max_images,
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

@app.get("/user-credits/{member_id}")
def get_user_credits(member_id: str):
    db = SessionLocal()
    user = db.query(User).filter(User.memberstack_id == member_id).first()

    if not user:
        return {"credits": 0}

    return {"credits": user.credits}

# =====================================================
#                     STATUS / POLLING
# =====================================================

@app.get("/status/{prediction_id}")
async def prediction_status(prediction_id: str):
    db = SessionLocal()
    prediction = replicate.predictions.get(prediction_id)

    output_url = None
    output = prediction.output
    

    def extract_url(item):
        if not item:
            return None
    
        # string direta
        if isinstance(item, str) and item.startswith("http"):
            return item
    
        # dict
        if isinstance(item, dict):
            for key in ["video", "output", "url", "image", "output_video"]:
                val = item.get(key)
    
                if isinstance(val, str) and val.startswith("http"):
                    return val
    
                if isinstance(val, dict):
                    inner = extract_url(val)
                    if inner:
                        return inner
    
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
            or NANOBANANA_TEMP_IMAGES.pop(prediction_id, None)
            or KLING_TEMP_IMAGES.pop(prediction_id, None)
            or GEN4_TEMP_IMAGES.pop(prediction_id, None)
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


# =========================================
# CHECK STATUS
# =========================================
@app.get("/status/{prediction_id}")
def check_status(prediction_id: str):
    prediction = replicate.predictions.get(prediction_id)

    if prediction.status == "succeeded" and output_url:
        meta = PREDICTION_META.get(prediction_id)
        if meta:
            final_upload = cloudinary.uploader.upload(prediction.output[0], folder="gallery")
            db = SessionLocal()
            creation = Creation(
                memberstack_id=meta["member_id"],
                prompt=meta["prompt"],
                model=meta["model"],
                result_url=final_upload["secure_url"]
            )
            db.add(creation)
            db.commit()
            db.close()
            del PREDICTION_META[prediction_id]

        return {"status": "done", "image": prediction.output[0]}

    return {"status": prediction.status}

# =========================================
# USER GALLERY
# =========================================
@app.get("/my-creations/{member_id}")
def my_creations(member_id: str):
    db = SessionLocal()
    creations = db.query(Creation)\
        .filter(Creation.memberstack_id == member_id)\
        .order_by(Creation.created_at.desc())\
        .all()
    db.close()

    return [
        {
            "id": c.id,
            "prompt": c.prompt,
            "image": c.image_url,
            "created_at": c.created_at
        }
        for c in creations
    ]

# =========================================
# MEMBERSTACK WEBHOOK (ADD CREDITS)
# =========================================
WEBHOOK_SECRET = os.getenv("MEMBERSTACK_WEBHOOK_SECRET")


def verify_memberstack_signature(raw_body: bytes, signature: str):
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


@app.post("/memberstack-webhook")
async def memberstack_webhook(request: Request):

    raw_body = await request.body()
    signature = request.headers.get("x-memberstack-signature")

    if not signature or not verify_memberstack_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    data = await request.json()

    event = data.get("type")
    member = data.get("data", {}).get("member", {})
    plan = data.get("data", {}).get("plan", {})

    member_id = member.get("id")
    credits = plan.get("metadata", {}).get("credits", 0)

    if not member_id:
        return {"status": "no member id"}

    db = SessionLocal()

    user = db.query(User).filter(User.memberstack_id == member_id).first()

    if not user:
        user = User(memberstack_id=member_id, credits=0)
        db.add(user)
        db.commit()
        db.refresh(user)

    if event in ["subscription.created", "subscription.renewed"]:
        user.credits += credits
        db.commit()

    db.close()

    return {"status": "secure webhook processed"}

# =========================================
# HEALTH CHECK
# =========================================
@app.get("/")
def root():
    return {"status": "API running"}

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
