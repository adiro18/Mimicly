from werkzeug.utils import secure_filename
import PyPDF2
from flask import Flask, request, render_template, send_from_directory, jsonify, Response
import os
import sqlite3
from werkzeug.utils import secure_filename
from TTS.api import TTS
from subprocess import run
import torch
import gc
from glob import glob
import mimetypes
import time
import subprocess

# === Flask App Setup ===
app = Flask(__name__, static_folder="static", template_folder="templates")

UPLOAD_FOLDER = "uploads"
PHOTO_FOLDER = os.path.join(UPLOAD_FOLDER, 'photos')
VOICE_FOLDER = os.path.join(UPLOAD_FOLDER, 'voices')
VIDEO_FOLDER = "D:/pro/SadTalker/uploads/videos"
RESULT_FOLDER = "results"
DB_PATH = "mimikly.db"

os.makedirs(PHOTO_FOLDER, exist_ok=True)
os.makedirs(VOICE_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# === Fix torch.load for XTTS compatibility ===
_original_load = torch.load
def patched_load(*args, **kwargs):
    kwargs["weights_only"] = False
    return _original_load(*args, **kwargs)
torch.load = patched_load

# === Database Init ===
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS photos (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, filename TEXT, data BLOB)''')
    c.execute('''CREATE TABLE IF NOT EXISTS voices (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, filename TEXT, file BLOB)''')
    c.execute('''CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, filename TEXT)''')
    conn.commit()
    conn.close()
init_db()

# Load TTS model
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
tts.to("cpu")

# === HTML Routes ===
@app.route("/")
def index():
    return render_template("Mimiclymain.html")

@app.route("/Mimiclymain.html")
def mimicly_main():
    return render_template("Mimiclymain.html")

@app.route("/GALLERY.html")
def gallery():
    return render_template("GALLERY.html")

@app.route("/generate.html")
def generate_page():
    return render_template("generate.html")

@app.route("/signuppage.html")
def signup():
    return render_template("signuppage.html")

@app.route("/loginmimicly.html")
def login():
    return render_template("loginmimicly.html")

@app.route("/uploadpage.html")
def upload_page():
    return render_template("uploadpage.html")

# === Upload Photo ===
@app.route("/upload/photo", methods=["POST"])
def upload_photo():
    if "photo" not in request.files or "photo_name" not in request.form:
        return jsonify({"error": "Missing photo or name"}), 400
    file = request.files["photo"]
    name = request.form["photo_name"]
    filename = secure_filename(file.filename)
    save_path = os.path.join(PHOTO_FOLDER, filename)
    file.save(save_path)
    with open(save_path, 'rb') as f:
        file_blob = f.read()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO photos (name, filename, data) VALUES (?, ?, ?)', (name, filename, file_blob))
    conn.commit()
    conn.close()
    return jsonify({"message": "Photo uploaded", "name": name, "filename": filename})

# === Upload Voice ===
@app.route("/upload/voice", methods=["POST"])
def upload_voice():
    if "voice" not in request.files or "voice_name" not in request.form:
        return jsonify({"error": "Missing voice or name"}), 400
    file = request.files["voice"]
    name = request.form["voice_name"]
    filename = secure_filename(file.filename)
    save_path = os.path.join(VOICE_FOLDER, filename)
    file.save(save_path)
    with open(save_path, 'rb') as f:
        file_blob = f.read()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO voices (name, filename, file) VALUES (?, ?, ?)', (name, filename, file_blob))
    conn.commit()
    conn.close()
    return jsonify({"message": "Voice uploaded", "name": name, "filename": filename})

# === Serve Images from DB or Disk ===
@app.route("/view/photo/<filename>")
def view_photo(filename):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT data FROM photos WHERE filename=?', (filename,))
    result = c.fetchone()
    conn.close()
    if result and result[0]:
        return Response(result[0], mimetype='image/jpeg')
    return send_from_directory(PHOTO_FOLDER, filename)

# === Serve Voice from DB or Disk ===
@app.route("/play/voice/<filename>")
def play_voice(filename):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT file FROM voices WHERE filename=?', (filename,))
    result = c.fetchone()
    conn.close()
    if result and result[0]:
        return Response(result[0], mimetype='audio/wav')
    return send_from_directory(VOICE_FOLDER, filename)

# === List Photos ===
@app.route("/photos")
def get_photos():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, filename FROM photos')
    photos = [{'name': row[0], 'filename': row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify(photos)

# === List Voices ===
@app.route("/voices")
def get_voices():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, filename FROM voices')
    voices = [{'name': row[0], 'filename': row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify(voices)

# === Generate Talking Video ===
@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    photo = data['photo']
    voice = data['voice']
    text = data['text']

    voice_path = os.path.join(VOICE_FOLDER, voice)
    photo_path = os.path.join(PHOTO_FOLDER, photo)
    tts_audio_path = os.path.join(VIDEO_FOLDER, f"{photo}_{voice}_{int(time.time())}.wav")

    try:
        tts.tts_to_file(text=text, speaker_wav=voice_path, language="en", file_path=tts_audio_path)
    except Exception as e:
        return jsonify({"error": f"TTS failed: {str(e)}"}), 500

    torch.cuda.empty_cache()
    gc.collect()

    try:
        result = run([
            "py", r"D:\pro\SadTalker\inference.py",
            "--driven_audio", tts_audio_path,
            "--source_image", photo_path,
            "--preprocess", "full",
            "--result_dir", VIDEO_FOLDER,
            "--cpu"
        ], check=True, capture_output=True, text=True)

        print("=== SadTalker STDOUT ===")
        print(result.stdout)
        print("=== SadTalker STDERR ===")
        print(result.stderr)

    except subprocess.CalledProcessError as e:
        print("SadTalker crashed:")
        print("Return Code:", e.returncode)
        print("=== STDOUT ===")
        print(e.stdout)
        print("=== STDERR ===")
        print(e.stderr)
        return jsonify({"error": f"SadTalker failed. Return Code: {e.returncode}"}), 500

    video_candidates = glob(os.path.join(VIDEO_FOLDER, "**/*.mp4"), recursive=True)
    if not video_candidates:
        return jsonify({"error": "No video was generated"}), 500
    latest_video_path = max(video_candidates, key=os.path.getctime)
    video_name = os.path.basename(latest_video_path)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA table_info(videos)")
    columns = [col[1] for col in c.fetchall()]
    if 'data' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN data BLOB')
    with open(latest_video_path, 'rb') as f:
        video_blob = f.read()
    c.execute('INSERT INTO videos (name, filename, data) VALUES (?, ?, ?)', (video_name, video_name, video_blob))
    conn.commit()
    conn.close()

    return jsonify({"message": "Video generated", "filename": video_name})

# === Generate Talking Video from PDF ===
@app.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    photo = request.form.get('photo')
    voice = request.form.get('voice')
    pdf_file = request.files.get('pdf')
    if not photo or not voice or not pdf_file:
        return jsonify({"error": "Missing required fields"}), 400

    # Save PDF temporarily
    pdf_filename = secure_filename(pdf_file.filename)
    pdf_path = os.path.join("uploads", pdf_filename)
    pdf_file.save(pdf_path)

    # Extract text from PDF
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            pdf_text = "\n".join([page.extract_text() or "" for page in reader.pages])
    except Exception as e:
        return jsonify({"error": f"PDF extraction failed: {str(e)}"}), 500

    # Clean up PDF file
    try:
        os.remove(pdf_path)
    except Exception:
        pass

    # Generate TTS audio from extracted text
    voice_path = os.path.join(VOICE_FOLDER, voice)
    photo_path = os.path.join(PHOTO_FOLDER, photo)
    tts_audio_path = os.path.join(VIDEO_FOLDER, f"{photo}_{voice}_{int(time.time())}_pdf.wav")
    try:
        tts.tts_to_file(text=pdf_text, speaker_wav=voice_path, language="en", file_path=tts_audio_path)
    except Exception as e:
        return jsonify({"error": f"TTS failed: {str(e)}"}), 500

    torch.cuda.empty_cache()
    gc.collect()

    try:
        result = run([
            "py", r"D:\pro\SadTalker\inference.py",
            "--driven_audio", tts_audio_path,
            "--source_image", photo_path,
            "--preprocess", "full",
            "--result_dir", VIDEO_FOLDER,
            "--cpu"
        ], check=True, capture_output=True, text=True)
        print("=== SadTalker STDOUT ===")
        print(result.stdout)
        print("=== SadTalker STDERR ===")
        print(result.stderr)
    except subprocess.CalledProcessError as e:
        print("SadTalker crashed:")
        print("Return Code:", e.returncode)
        print("=== STDOUT ===")
        print(e.stdout)
        print("=== STDERR ===")
        print(e.stderr)
        return jsonify({"error": f"SadTalker failed. Return Code: {e.returncode}"}), 500

    video_candidates = glob(os.path.join(VIDEO_FOLDER, "**/*.mp4"), recursive=True)
    if not video_candidates:
        return jsonify({"error": "No video was generated"}), 500
    latest_video_path = max(video_candidates, key=os.path.getctime)
    video_name = os.path.basename(latest_video_path)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA table_info(videos)")
    columns = [col[1] for col in c.fetchall()]
    if 'data' not in columns:
        c.execute('ALTER TABLE videos ADD COLUMN data BLOB')
    with open(latest_video_path, 'rb') as f:
        video_blob = f.read()
    c.execute('INSERT INTO videos (name, filename, data) VALUES (?, ?, ?)', (video_name, video_name, video_blob))
    conn.commit()
    conn.close()

    return jsonify({"message": "Video generated", "filename": video_name})

# === Gallery ===
@app.route("/gallery")
def get_gallery():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, filename FROM videos')
    videos = [{'name': row[0], 'filename': row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify(videos)

# === Delete Video ===
@app.route("/gallery/<filename>", methods=["DELETE"])
def delete_video(filename):
    path = os.path.join(VIDEO_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM videos WHERE filename=?', (filename,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Video deleted'})
    return jsonify({'error': 'File not found'}), 404

# === Delete Photo ===
@app.route("/photos/<filename>", methods=["DELETE"])
def delete_photo(filename):
    path = os.path.join(PHOTO_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM photos WHERE filename=?', (filename,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Photo deleted'})

# === Delete Voice ===
@app.route("/voices/<filename>", methods=["DELETE"])
def delete_voice(filename):
    path = os.path.join(VOICE_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM voices WHERE filename=?', (filename,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Voice deleted'})

# === Static Serve Helper ===
@app.route("/uploads/<folder>/<filename>")
def uploaded_file(folder, filename):
    folder_map = {'photos': PHOTO_FOLDER, 'voices': VOICE_FOLDER, 'videos': VIDEO_FOLDER}
    return send_from_directory(folder_map[folder], filename)

# === Dedicated Video Upload Route ===
@app.route("/uploads/videos/<filename>")
def uploaded_video(filename):
    return send_from_directory(VIDEO_FOLDER, filename, mimetype='video/mp4')

# === Run ===
if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
