from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import shutil
import uuid
import os
import tempfile

# =========================
# SAFE IMPORT (IMPORTANT)
# =========================
try:
    from PDF_TOOLTIPS_URL import run_processing
except Exception as e:
    print("⚠️ run_processing not found, using fallback:", e)

    def run_processing(pdf_path, excel_path, output_pdf, report_path):
        """
        Fallback pour éviter crash Render
        """
        with open(report_path, "w") as f:
            f.write("Processing fallback mode (module missing)\n")

        # copie simple du PDF en output
        shutil.copy(pdf_path, output_pdf)

        return {
            "status": "fallback",
            "message": "run_processing module missing"
        }


# =========================
# FASTAPI INIT
# =========================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = tempfile.gettempdir()


# =========================
# ROUTES
# =========================
@app.get("/")
def home():
    return {"status": "API running 🚀"}


@app.post("/process")
async def process_files(
    pdf: UploadFile = File(...),
    excel: UploadFile = File(...)
):

    try:
        uid = str(uuid.uuid4())

        pdf_path = os.path.join(TEMP_DIR, f"{uid}.pdf")
        excel_path = os.path.join(TEMP_DIR, f"{uid}.xlsx")
        output_pdf = os.path.join(TEMP_DIR, f"{uid}_output.pdf")
        report_path = os.path.join(TEMP_DIR, f"{uid}.txt")

        # Save PDF
        with open(pdf_path, "wb") as f:
            shutil.copyfileobj(pdf.file, f)

        # Save Excel
        with open(excel_path, "wb") as f:
            shutil.copyfileobj(excel.file, f)

        # Processing
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


@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(TEMP_DIR, filename)

    if not os.path.exists(file_path):
        return {"error": "Fichier introuvable"}

    return FileResponse(file_path)