"""
backend/app.py – opgekuiste, volledige versie
Geschikt voor lokale tests met Whisper‑transcriptie + Gemini‑feedback.
"""

from flask import Flask, request, jsonify
import os
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.utils import secure_filename
import traceback
import whisper
from dotenv import load_dotenv
from google import generativeai as genai

# --------------------------------------------------
# .env laden (GOOGLE_API_KEY, etc.)
load_dotenv()

# --------------------------------------------------
# AI‑prompt (Plan van Aanpak)
PLAN_VAN_AANPAK = """
Je bent een professionele presentatiecoach. Je krijgt hieronder een transcript van een
studentenpresentatie. Geef gestructureerde, constructieve feedback op:
1. Structuur: duidelijkheid van inleiding, kern en afsluiting.
2. Taalgebruik: begrijpelijk en passend Nederlands.
3. Spreektempo: aangenaam, niet te snel of traag.
4. Intonatie: variatie in toon om de aandacht vast te houden.
5. Non-verbaal: schatting van oogcontact, houding en gebaren (op basis van transcript).
6. Algemene tips: noem concrete verbeterpunten en wat goed ging.
Antwoord in paragrafen en gebruik opsommingstekens voor tips.
"""

# --------------------------------------------------
# Flask‑initialisatie en logging
app = Flask(__name__)

from flask_cors import CORS
app = Flask(__name__)
CORS(app)        # ← voegt Access-Control-Allow-Origin: * toe

if not os.path.exists("logs"):
    os.makedirs("logs")

file_handler = RotatingFileHandler("logs/app.log", maxBytes=10_240, backupCount=10)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s: %(message)s [%(pathname)s:%(lineno)d]")
)
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info("Applicatie gestart")

# --------------------------------------------------
# Upload‑configuratie
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# --------------------------------------------------
# Whisper‑model laden (één keer)
MODEL = whisper.load_model("base")

# --------------------------------------------------
# Helper: video/audio → tekst

def transcribe_video(video_path: str) -> str:
    app.logger.info(f"Start transcriptie: {video_path}")
    try:
        result = MODEL.transcribe(video_path)
        app.logger.info("Transcriptie voltooid")
        return result["text"].strip()
    except Exception as e:
        app.logger.error(f"Fout bij transcriptie: {e}")
        raise

# --------------------------------------------------
# Helper: prompt → Gemini‑feedback

def vraag_feedback(prompt: str) -> str:
    """Stuurt de prompt naar Gemini en geeft de tekstuele feedback terug."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY ontbreekt.")

    # Stel de API-key in voor de huidige procesrun
    genai.configure(api_key=api_key)

    # Kies een beschikbaar tekstmodel (zie list_models)
    model = genai.GenerativeModel("models/gemini-1.5-pro-latest")

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # Log volledige traceback zodat we weten wat er misgaat
        app.logger.error("Gemini API-fout:", exc_info=True)
        raise RuntimeError("GOOGLE_API_KEY ontbreekt in omgevingsvariabelen.")

    model = genai.GenerativeModel(model_name="gemini-2.5-pro", api_key=api_key)
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        app.logger.error(f"Gemini API‑fout: {e}")
        raise

# --------------------------------------------------
# Routes

@app.route("/upload", methods=["POST"])
def upload_video():
    app.logger.info(f"FILES KEYS: {list(request.files.keys())}")

    if "file" not in request.files:
        return jsonify({"error": "Geen video gevonden in het verzoek."}), 400

    video = request.files["file"]
    if video.filename == "":
        return jsonify({"error": "Geen bestand geselecteerd."}), 400

    allowed = {"mp4", "mov", "avi", "mkv", "mp3", "wav"}
    if "." not in video.filename or video.filename.rsplit(".", 1)[1].lower() not in allowed:
        return jsonify({"error": "Ongeldig bestandsformaat."}), 400

    filename = secure_filename(video.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    try:
        video.save(filepath)
        app.logger.info(f"Video opgeslagen: {filepath}")

        # ----------- transcriptie ----------
        try:
            transcript = transcribe_video(filepath)
        except Exception as e:
            app.logger.error(f"Transcriptie mislukt: {e}")
            return jsonify({"error": "Kon de video niet transcriberen."}), 500

        # ----------- AI-feedback -----------
        volledige_prompt = PLAN_VAN_AANPAK + "\n\nTranscript:\n" + transcript
        try:
            feedback = vraag_feedback(volledige_prompt)
            app.logger.info("AI-feedback succesvol opgehaald")
        except Exception as e:
            app.logger.error(f"Fout bij AI-aanroep: {e}", exc_info=True)
            return jsonify({"error": "Kon geen AI-feedback ophalen."}), 500

        # ----------- response --------------
        return jsonify({
            "message": "Video verwerkt.",
            "filepath": filepath,
            "transcript": transcript,
            "feedback": feedback
        }), 200

    except Exception as e:
        app.logger.error(f"Onverwachte fout: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Er is iets misgegaan op de server."}), 500

# --------------------------------------------------
if __name__ == "__main__":
    print("Server wordt gestart op http://127.0.0.1:5000")
    app.run(debug=True)