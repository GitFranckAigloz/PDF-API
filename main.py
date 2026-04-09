from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import shutil
import uuid
import os
import tempfile

from PDF_TOOLTIPS_URL import run_processing

# Initialisation API
app = FastAPI()

# CORS (important pour accès web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dossier temporaire compatible cloud
TEMP_DIR = tempfile.gettempdir()


# Route test
@app.get("/")
def home():
    return {"message": "API OK"}


# Route principale : traitement PDF + Excel
@app.post("/process")
async def process_files(pdf: UploadFile = File(...), excel: UploadFile = File(...)):

    try:
        # Génération ID unique
        uid = str(uuid.uuid4())

        # Chemins fichiers
        pdf_path = os.path.join(TEMP_DIR, f"{uid}.pdf")
        excel_path = os.path.join(TEMP_DIR, f"{uid}.xlsx")
        output_pdf = os.path.join(TEMP_DIR, f"{uid}_output.pdf")
        report_path = os.path.join(TEMP_DIR, f"{uid}.txt")

        # Sauvegarde PDF
        with open(pdf_path, "wb") as f:
            shutil.copyfileobj(pdf.file, f)

        # Sauvegarde Excel
        with open(excel_path, "wb") as f:
            shutil.copyfileobj(excel.file, f)

        # Traitement
        results = run_processing(pdf_path, excel_path, output_pdf, report_path)

        return {
            "status": "success",
            "pdf_url": f"/download/{uid}_output.pdf",
            "report_url": f"/download/{uid}.txt",
            "stats": results
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# Route téléchargement fichiers
@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(TEMP_DIR, filename)

    if not os.path.exists(file_path):
        return {"error": "Fichier introuvable"}

    return FileResponse(file_path)