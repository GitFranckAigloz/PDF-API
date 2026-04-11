from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import shutil
import uuid
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =========================
# PROCESSING IMPORT
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gitfranckaigloz.github.io",
        "http://localhost:5500",
        "null"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = "/tmp"
BASE_URL = "https://pdf-api-oj86.onrender.com"


# =========================
# EMAIL CONFIG (GMAIL)
# =========================
EMAIL_USER = "TON_EMAIL@gmail.com"
EMAIL_PASS = "TON_APP_PASSWORD"  # ⚠️ pas ton mot de passe normal


def send_email(to_email, pdf_url):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = "Votre PDF est prêt"

    body = f"""
    Bonjour 👋

    Votre fichier PDF est prêt !

    👉 Télécharger ici :
    {pdf_url}

    Merci !
    """

    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL_USER, EMAIL_PASS)
    server.send_message(msg)
    server.quit()


# =========================
# PROCESS ENDPOINT
# =========================
@app.post("/process")
async def process_files(
    pdf: UploadFile = File(...),
    excel: UploadFile = File(...),
    email: str = Form(...)
):

    if not email:
        raise HTTPException(status_code=400, detail="Email manquant")

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
        raise HTTPException(status_code=500, detail="PDF non généré")

    pdf_url = f"{BASE_URL}/download/{uid}_output.pdf"
    report_url = f"{BASE_URL}/download/{uid}.txt"

    # EMAIL SEND
    try:
        send_email(email, pdf_url)
    except Exception as e:
        print("EMAIL ERROR:", e)

    return {
        "status": "success",
        "email_sent_to": email,
        "pdf_url": pdf_url,
        "report_url": report_url,
        "stats": results
    }


# =========================
# DOWNLOAD
# =========================
@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(TEMP_DIR, filename)

    if not os.path.exists(file_path):
        return {"error": "Fichier introuvable"}

    return FileResponse(file_path)
