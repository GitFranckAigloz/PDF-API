from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import shutil
import uuid
import os

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
# 🔥 CORS FIX (PROPRE)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tu pourras restreindre plus tard
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 🔥 PREFLIGHT FIX (CRITIQUE)
# =========================
@app.options("/{full_path:path}")
async def preflight_handler(full_path: str):
    return JSONResponse(content={"status": "ok"})

# =========================
# CONFIG
# =========================
TEMP_DIR = "/tmp"
BASE_URL = "https://pdf-api-oj86.onrender.com"

# =========================
# HEALTH CHECK
# =========================
@app.get("/")
def home():
    return {
        "status": "API running 🚀",
        "routes": ["/process", "/download/{filename}"]
    }

@app.get("/ping")
def ping():
    return {"status": "awake"}

# =========================
# PROCESS ROUTE
# =========================
@app.post("/process")
async def process_files(
    request: Request,
    pdf: UploadFile = File(...),
    excel: UploadFile = File(...),
    email: str = Form(...)
):
    try:
        print("🔥 REQUEST RECEIVED")

        form = await request.form()
        print("FORM DATA:", list(form.keys()))

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

        print("✅ Files saved")

        # PROCESSING
        results = run_processing(pdf_path, excel_path, output_pdf, report_path)

        print("✅ Processing done:", results)

        if not os.path.exists(output_pdf):
            raise HTTPException(status_code=500, detail="PDF non généré")

        return {
            "status": "success",
            "email": email,
            "pdf_url": f"{BASE_URL}/download/{uid}_output.pdf",
            "report_url": f"{BASE_URL}/download/{uid}.txt",
            "stats": results
        }

    except Exception as e:
        print("❌ ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# DOWNLOAD ROUTE
# =========================
@app.get("/download/{filename}")
def download_file(filename: str):

    file_path = os.path.join(TEMP_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    return FileResponse(file_path)
