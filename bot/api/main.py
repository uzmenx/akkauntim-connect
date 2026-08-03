from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Loyiha papkasini topish uchun sys.path ga qo'shamiz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from bot.api.routes import prediction, monitoring

app = FastAPI(title="Akkauntim Connect - Bot API")

# Frontend (localhost) ulanishida CORS xatosini oldini olish
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # yoki ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route larni ulash
app.include_router(prediction.router)
app.include_router(monitoring.router)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Bot API is running"}

# Dasturni ishga tushirish uchun quyidagi buyruqdan foydalaniladi:
# uvicorn bot.api.main:app --reload --port 8000
