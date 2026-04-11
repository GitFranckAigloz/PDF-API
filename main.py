from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import shutil
import uuid
import os
import resend

# =========================
# CONFIG RESEND
# =========================
resend.api_key = os.getenv("RESEND_API_KEY")

def send_email(to_email, pdf_url, report_url):
    try:
        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": [to_email],
            "subject": "Ton PDF est prêt 🚀",
            "html": f"""
                <h2>✅ Traitement terminé</h2>
                <p>Ton fichier est prêt :</p>
                <p><a href="{pdf_url}">📄 Télécharger le PDF</a></p>
                <p><a href="{report_url}">📊 Voir le rapport</a></p>
            """
        })
        print("📧 Email envoyé à", to_email)
    except Exception as e:
        print("❌ Erreur email:", str(e))


# =========================
# SAFE IMPORT
# =========================
try:
    from PDF_TOOLTIPS_URL import run_processing
except Exception:
    def run_processing(pdf_path, excel_path, output_pdf, report_path):
        with open(report_path, "w") as f:
            f.write("Fallback mode\n")

        shutil.copy(pdf_path, output_pdf)

        return {"status": "fallback"}


# =========================
# APP INIT
# =========================
app = FastAPI()

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# PREFLIGHT
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
# ROUTES
# =========================
@app.get("/")
def home():
    return {"status": "API running 🚀"}

@app.post("/process")
async def process_files(
    request: Request,
    pdf: UploadFile = File(...),
    excel: UploadFile = File(...),
    email: str = Form(...)
):
    try:
        uid = str(uuid.uuid4())

        pdf_path = os.path.join(TEMP_DIR, f"{uid}.pdf")
        excel_path = os.path.join(TEMP_DIR, f"{uid}.xlsx")
        output_pdf = os.path.join(TEMP_DIR, f"{uid}_output.pdf")
        report_path = os.path.join(TEMP_DIR, f"{uid}.txt")

        # SAVE
        with open(pdf_path, "wb") as f:
            shutil.copyfileobj(pdf.file, f)

        with open(excel_path, "wb") as f:
            shutil.copyfileobj(excel.file, f)

        # PROCESS
        run_processing(pdf_path, excel_path, output_pdf, report_path)

        if not os.path.exists(output_pdf):
            raise HTTPException(500, "PDF non généré")

        pdf_url = f"{BASE_URL}/download/{uid}_output.pdf"
        report_url = f"{BASE_URL}/download/{uid}.txt"

        # 🔥 SEND EMAIL
        send_email(email, pdf_url, report_url)

        return {
            "status": "success",
            "email": email,
            "pdf_url": pdf_url,
            "report_url": report_url
        }

    except Exception as e:
        print("❌ ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filename}")
def download_file(filename: str):
    path = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Fichier introuvable")
    return FileResponse(path)
