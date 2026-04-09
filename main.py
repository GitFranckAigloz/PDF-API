from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import shutil
import uuid
import os
import tempfile

# =========================
# SAFE IMPORT
# =========================
try:
    from PDF_TOOLTIPS_URL import run_processing
except Exception as e:
    print("⚠️ run_processing not found, using fallback:", e)

    def run_processing(pdf_path, excel_path, output_pdf, report_path):
        with open(report_path, "w") as f:
            f.write("Fallback mode\n")

        shutil.copy(pdf_path, output_pdf)

        return {"status": "fallback"}


# =========================
# INIT
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

# 👉 IMPORTANT : mets TON URL Render ici
BASE_URL = "https://pdf-api-oj86.onrender.com"


# =========================
# ROUTES
# =========================
@app.get("/")
def home():
    return {"status": "API running 🚀"}


@app.post("/process")
async def process_files(pdf: UploadFile = File(...), excel: UploadFile = File(...)):

    try:
        uid = str(uuid.uuid4())

        pdf_path = os.path.join(TEMP_DIR, f"{uid}.pdf")
        excel_path = os.path.join(TEMP_DIR, f"{uid}.xlsx")
        output_pdf = os.path.join(TEMP_DIR, f"{uid}_output.pdf")
        report_path = os.path.join(TEMP_DIR, f"{uid}.txt")

        print("📄 PDF path:", pdf_path)
        print("📊 Excel path:", excel_path)
        print("📤 Output PDF:", output_pdf)

        # Save files
        with open(pdf_path, "wb") as f:
            shutil.copyfileobj(pdf.file, f)

        with open(excel_path, "wb") as f:
            shutil.copyfileobj(excel.file, f)

        # Processing
        results = run_processing(pdf_path, excel_path, output_pdf, report_path)

        # Vérification fichier généré
        if not os.path.exists(output_pdf):
            return {
                "status": "error",
                "message": "Output PDF not generated"
            }

        # URL complète
        pdf_url = f"{BASE_URL}/download/{uid}_output.pdf"
        report_url = f"{BASE_URL}/download/{uid}.txt"

        print("✅ Download URL:", pdf_url)

        return {
            "status": "success",
            "pdf_url": pdf_url,
            "report_url": report_url,
            "stats": results
        }

    except Exception as e:
        print("❌ ERROR:", str(e))
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(TEMP_DIR, filename)

    print("⬇️ Download request:", file_path)

    if not os.path.exists(file_path):
        print("❌ File not found")
        return {"error": "Fichier introuvable"}

    return FileResponse(file_path)