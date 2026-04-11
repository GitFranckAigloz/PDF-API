from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import shutil
import uuid
import os
import tempfile

try:
    from PDF_TOOLTIPS_URL import run_processing
except Exception:
    def run_processing(pdf_path, excel_path, output_pdf, report_path):
        with open(report_path, "w") as f:
            f.write("Fallback mode\n")

        shutil.copy(pdf_path, output_pdf)

        return {"status": "fallback"}


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod → mettre ton domaine
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = "/tmp"  # important pour Render

BASE_URL = "https://pdf-api-oj86.onrender.com"


@app.get("/")
def home():
    return {"status": "API running 🚀"}


@app.post("/process")
async def process_files(
    pdf: UploadFile = File(...),
    excel: UploadFile = File(...),
    email: str = Form(...)
):

    uid = str(uuid.uuid4())

    pdf_path = os.path.join(TEMP_DIR, f"{uid}.pdf")
    excel_path = os.path.join(TEMP_DIR, f"{uid}.xlsx")
    output_pdf = os.path.join(TEMP_DIR, f"{uid}_output.pdf")
    report_path = os.path.join(TEMP_DIR, f"{uid}.txt")

    # Save files
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(pdf.file, f)

    with open(excel_path, "wb") as f:
        shutil.copyfileobj(excel.file, f)

    # Processing
    results = run_processing(pdf_path, excel_path, output_pdf, report_path)

    if not os.path.exists(output_pdf):
        return {"status": "error", "message": "Output PDF not generated"}

    return {
        "status": "success",
        "email": email,
        "pdf_url": f"{BASE_URL}/download/{uid}_output.pdf",
        "report_url": f"{BASE_URL}/download/{uid}.txt",
        "stats": results
    }


@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(TEMP_DIR, filename)

    if not os.path.exists(file_path):
        return {"error": "Fichier introuvable"}

    return FileResponse(file_path)