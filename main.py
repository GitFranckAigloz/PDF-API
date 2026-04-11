from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import shutil
import uuid
import os
import tempfile

# =========================
# SAFE IMPORT (PROCESSING)
# =========================
try:
    from PDF_TOOLTIPS_URL import run_processing
except Exception:
    def run_processing(pdf_path, excel_path, output_pdf, report_path):
        with open(report_path, "w") as f:
            f.write("Fallback mode\n")

        shutil.copy(pdf_path, output_pdf)

        return {
            "status": "fallback",
            "pages": 0,
            "items": 0
        }


# =========================
# APP INIT
# =========================
app = FastAPI()


# =========================
# CORS (FIX STABLE)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gitfranckaigloz.github.io",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "null"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# CONFIG
# =========================
TEMP_DIR = "/tmp"
BASE_URL = "https://pdf-api-oj86.onrender.com"


# =========================
# HEALTH CHECK ROUTE
# =========================
@app.get("/")
def home():
    return {
        "status": "API running 🚀",
        "routes": ["/process", "/download/{filename}"]
    }


# =========================
# PROCESS ROUTE
# =========================
@app.post("/process")
async def process_files(
    pdf: UploadFile = File(...),
    excel: UploadFile = File(...),
    email: str = Form(...)
):

    if not pdf or not excel:
        raise HTTPException(status_code=400, detail="Fichiers manquants")

    if not email:
        raise HTTPException(status_code=400, detail="Email manquant")

    uid = str(uuid.uuid4())

    pdf_path = os.path.join(TEMP_DIR, f"{uid}.pdf")
    excel_path = os.path.join(TEMP_DIR, f"{uid}.xlsx")
    output_pdf = os.path.join(TEMP_DIR, f"{uid}_output.pdf")
    report_path = os.path.join(TEMP_DIR, f"{uid}.txt")

    # SAVE FILES
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(pdf.file, f)

    with open(excel_path, "wb") as f:
        shutil.copyfileobj(excel.file, f)

    # PROCESSING
    results = run_processing(pdf_path, excel_path, output_pdf, report_path)

    if not os.path.exists(output_pdf):
        raise HTTPException(status_code=500, detail="PDF non généré")

    return {
        "status": "success",
        "email": email,
        "pdf_url": f"{BASE_URL}/download/{uid}_output.pdf",
        "report_url": f"{BASE_URL}/download/{uid}.txt",
        "stats": results
    }


# =========================
# DOWNLOAD ROUTE
# =========================
@app.get("/download/{filename}")
def download_file(filename: str):

    file_path = os.path.join(TEMP_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    return FileResponse(file_path)
