import os
import re
import pandas as pd
import pytesseract
from PIL import Image
from io import BytesIO
from google.cloud import vision
from google.oauth2 import service_account
import streamlit as st

# ================= CONFIG =================
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"  # Ajustar si se usa local

# Google Vision config (leyendo desde st.secrets)
clave_json = st.secrets["GCP_KEY"]
credenciales = service_account.Credentials.from_service_account_info(clave_json)
cliente_vision = vision.ImageAnnotatorClient(credentials=credenciales)

# ============== FUNCIONES OCR ==============
def ocr_google_vision(imagen_bytes):
    try:
        image = vision.Image(content=imagen_bytes)
        response = cliente_vision.text_detection(image=image)

        if response.error.message:
            st.error(f"🛑 Error en Google Vision: {response.error.message}")
            return ""

        if response.text_annotations:
            return response.text_annotations[0].description.strip()

        return ""

    except Exception as e:
        st.exception(f"❌ Error procesando la imagen: {e}")
        return ""

# ============== EXTRACCIÓN DE DATOS ==============
def extraer_datos(texto):
    nombre = re.findall(r"Villafane.*Antonella", texto, re.IGNORECASE)
    acompanante = re.findall(r"Gonzales.*Cesar", texto, re.IGNORECASE)
    comprobante = re.findall(r"(?:Scontrino Fiscale|Numero)[^\d]*(\d+)", texto, re.IGNORECASE)
    fecha = re.findall(r"\d{2}/\d{2}/\d{4}", texto)
    servicio = re.findall(r"Perno[a-zA-Z\s]+(?:TRIPLA|DOPPIA|SINGOLA)?", texto, re.IGNORECASE)
    pago = re.findall(r"POS|ONLINE|CONTANTI", texto, re.IGNORECASE)
    subtotal = re.findall(r"(\d{2},\d{2})\s*€", texto)
    total = re.findall(r"(\d{2},\d{2})\s*€\s*$", texto, re.MULTILINE)

    subtotal_val = subtotal[0] if subtotal else ""
    total_val = total[0] if total else ""
    iva_val = ""
    try:
        if subtotal_val and total_val:
            sub = float(subtotal_val.replace(",", "."))
            tot = float(total_val.replace(",", "."))
            iva_val = str(round(tot - sub, 2)).replace(".", ",")
    except:
        iva_val = ""

    return {
        "Nombre titular": nombre[0] if nombre else "",
        "Acompañante": acompanante[0] if acompanante else "",
        "Número comprobante": comprobante[0] if comprobante else "",
        "Fecha servicio": fecha[0] if fecha else "",
        "Servicio prestado": servicio[0] if servicio else "",
        "Método de pago": pago[0] if pago else "",
        "Subtotal (€)": subtotal_val,
        "IVA (€)": iva_val,
        "IVA (%)": "10%",
        "Total (€)": total_val,
        "Texto completo": texto[:1000]
    }

# ============== INTERFAZ STREAMLIT ==============
st.set_page_config(page_title="OCR Express", layout="centered")
st.title("🧾 OCR Express para Facturas")
st.caption("Subí tus imágenes o PDFs y obtené los datos automáticamente")

archivos = st.file_uploader("Seleccioná una o varias facturas:", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)

if archivos:
    registros = []
    for archivo in archivos:
        bytes_imagen = archivo.read()
        texto = ocr_google_vision(bytes_imagen)
        datos = extraer_datos(texto)
        datos["Archivo"] = archivo.name
        datos["OCR_Fuente"] = "Google Vision"
        registros.append(datos)

    df = pd.DataFrame(registros)
    st.success
