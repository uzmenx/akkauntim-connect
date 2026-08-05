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

import sqlite3

def init_dbs():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    db_files = ["decisions_log.db", "bot_learning.db"]
    for db in db_files:
        db_path = os.path.join(root_dir, db)
        try:
            conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=30000;")
            conn.close()
        except Exception as e:
            print(f"DB Init Warning for {db}: {e}")

init_dbs()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Bot API is running, SQLite WAL mode enabled."}

# Dasturni ishga tushirish uchun quyidagi buyruqdan foydalaniladi:
# uvicorn bot.api.main:app --reload --port 8000
