import os
from flask import Flask, request, jsonify, send_from_directory, Response
from werkzeug.utils import secure_filename
from TTS.api import TTS
import subprocess
import sqlite3
from flask_cors import CORS
import mimetypes
import time  # Added for unique filenames

UPLOAD_FOLDER = 'uploads'
PHOTO_FOLDER = os.path.join(UPLOAD_FOLDER, 'photos')
VOICE_FOLDER = os.path.join(UPLOAD_FOLDER, 'voices')
VIDEO_FOLDER = os.path.join(UPLOAD_FOLDER, 'videos')
DB_PATH = 'mimikly.db'

os.makedirs(PHOTO_FOLDER, exist_ok=True)
os.makedirs(VOICE_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS photos (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, filename TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS voices (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, filename TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, filename TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/upload/photo', methods=['POST'])
def upload_photo():
    if 'photo_name' not in request.form:
        return jsonify({'error': 'Missing photo_name in form data'}), 400
    if 'photo' not in request.files:
        return jsonify({'error': 'No photo file uploaded'}), 400
    name = request.form['photo_name']
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(file.filename)
    path = os.path.join(PHOTO_FOLDER, filename)
    try:
        file.save(path)
        # Read file as binary for BLOB storage
        with open(path, 'rb') as f:
            file_blob = f.read()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Add a 'data' column if not exists
        c.execute("PRAGMA table_info(photos)")
        columns = [col[1] for col in c.fetchall()]
        if 'data' not in columns:
            c.execute('ALTER TABLE photos ADD COLUMN data BLOB')
        c.execute('INSERT INTO photos (name, filename, data) VALUES (?, ?, ?)', (name, filename, file_blob))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Photo uploaded', 'name': name, 'filename': filename}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to save photo: {str(e)}'}), 500

@app.route('/upload/voice', methods=['POST'])
def upload_voice():
    # Error handling for missing form fields or files
    if 'voice_name' not in request.form:
        return jsonify({'error': 'Missing voice_name in form data'}), 400
    if 'voice' not in request.files:
        return jsonify({'error': 'No voice file uploaded'}), 400
    name = request.form['voice_name']
    file = request.files['voice']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(file.filename)
    path = os.path.join(VOICE_FOLDER, filename)
    try:
        file.save(path)
        # Read file as binary for BLOB storage
        with open(path, 'rb') as f:
            file_blob = f.read()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Add a 'file' column if not exists
        c.execute("PRAGMA table_info(voices)")
        columns = [col[1] for col in c.fetchall()]
        if 'file' not in columns:
            c.execute('ALTER TABLE voices ADD COLUMN file BLOB')
        c.execute('INSERT INTO voices (name, filename, file) VALUES (?, ?, ?)', (name, filename, file_blob))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Voice uploaded', 'name': name, 'filename': filename}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to save voice: {str(e)}'}), 500

@app.route('/photos', methods=['GET'])
def get_photos():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, filename FROM photos')
    photos = [{'name': row[0], 'filename': row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify(photos)

@app.route('/voices', methods=['GET'])
def get_voices():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, filename FROM voices')
    voices = [{'name': row[0], 'filename': row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify(voices)

# NEW ENDPOINT: Serve voice files from database blob or file system
@app.route('/play/voice/<filename>', methods=['GET'])
def play_voice(filename):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT file, filename FROM voices WHERE filename = ?', (filename,))
        result = c.fetchone()
        conn.close()
        
        if result is None:
            return jsonify({'error': 'Voice file not found'}), 404
        
        file_blob, original_filename = result
        
        # If blob data exists, serve from database
        if file_blob is not None:
            # Determine the MIME type based on file extension
            mime_type, _ = mimetypes.guess_type(original_filename)
            if mime_type is None:
                # Default to audio/wav if we can't determine the type
                mime_type = 'audio/wav'
            
            # Return the blob data as a response with appropriate headers
            return Response(
                file_blob,
                mimetype=mime_type,
                headers={
                    'Content-Disposition': f'inline; filename="{original_filename}"',
                    'Content-Type': mime_type
                }
            )
        else:
            # Fall back to serving from file system
            file_path = os.path.join(VOICE_FOLDER, filename)
            if os.path.exists(file_path):
                return send_from_directory(VOICE_FOLDER, filename)
            else:
                return jsonify({'error': 'Voice file data not found in database or file system'}), 404
        
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve voice file: {str(e)}'}), 500

# OPTIONAL: Similar endpoint for photos if needed  
@app.route('/view/photo/<filename>', methods=['GET'])
def view_photo(filename):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT data, filename FROM photos WHERE filename = ?', (filename,))
        result = c.fetchone()
        conn.close()
        
        if result is None:
            return jsonify({'error': 'Photo file not found'}), 404
        
        file_blob, original_filename = result
        
        # If blob data exists, serve from database
        if file_blob is not None:
            # Determine the MIME type based on file extension
            mime_type, _ = mimetypes.guess_type(original_filename)
            if mime_type is None:
                # Default to image/jpeg if we can't determine the type
                mime_type = 'image/jpeg'
            
            # Return the blob data as a response with appropriate headers
            return Response(
                file_blob,
                mimetype=mime_type,
                headers={
                    'Content-Disposition': f'inline; filename="{original_filename}"',
                    'Content-Type': mime_type
                }
            )
        else:
            # Fall back to serving from file system
            file_path = os.path.join(PHOTO_FOLDER, filename)
            if os.path.exists(file_path):
                return send_from_directory(PHOTO_FOLDER, filename)
            else:
                return jsonify({'error': 'Photo file data not found in database or file system'}), 404
        
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve photo file: {str(e)}'}), 500

@app.route('/generate', methods=['POST'])
def generate_video():
    data = request.json
    photo = data['photo']
    text = data['text']
    voice = data.get('voice')  # Optional for TTS

    photo_path = os.path.join(PHOTO_FOLDER, photo)

    # === Determine if using TTS or uploaded voice ===
    if voice and voice.endswith('.wav'):
        # Case: Using uploaded voice file
        voice_path = os.path.join(VOICE_FOLDER, voice)
    else:
        # Case: Using only text input (TTS)
        voice_path = None

    # Generate TTS audio
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
    photo_name = os.path.splitext(photo)[0]
    voice_name = os.path.splitext(voice)[0] if voice else 'tts'
    timestamp = int(time.time())
    tts_audio_name = f"{photo_name}_{voice_name}_{timestamp}.wav"
    tts_audio_path = os.path.join(VIDEO_FOLDER, tts_audio_name)
    
    if voice_path:
        tts.tts_to_file(text=text, speaker_wav=voice_path, language="en", file_path=tts_audio_path)
    else:
        tts.tts_to_file(text=text, language="en", file_path=tts_audio_path)

    # Generate video
    video_name = f"{tts_audio_name.replace('.wav', '')}.mp4"

    # Verify audio and photo paths exist before running SadTalker
    if not os.path.exists(tts_audio_path):
        return jsonify({'error': f'TTS audio was not generated at: {tts_audio_path}'}), 500
    if not os.path.exists(photo_path):
        return jsonify({'error': f'Photo not found at: {photo_path}'}), 500
    print(f"tts_audio_path: {tts_audio_path}")
    print(f"photo_path: {photo_path}")
    try:
        subprocess.run([
            'python', 'D:/sadd/SadTalker/inference.py',
            '--driven_audio', tts_audio_path,
            '--source_image', photo_path,
            '--preprocess', 'full',
            '--result_dir', VIDEO_FOLDER,
            # '--enhancer', 'gfpgan',
            '--cpu'
        ], check=True)
    except Exception as e:
        print("SadTalker subprocess error:", e)
        return jsonify({'error': f'SadTalker failed: {e}'}), 500

    # Save to DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO videos (name, filename) VALUES (?, ?)', (video_name, video_name))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Video generated', 'filename': video_name})

@app.route('/gallery', methods=['GET'])
def get_gallery():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, filename FROM videos')
    videos = [{'name': row[0], 'filename': row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify(videos)

@app.route('/gallery/<filename>', methods=['DELETE'])
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

@app.route('/uploads/<folder>/<filename>')
def uploaded_file(folder, filename):
    folder_map = {'photos': PHOTO_FOLDER, 'voices': VOICE_FOLDER, 'videos': VIDEO_FOLDER}
    return send_from_directory(folder_map[folder], filename)

if __name__ == '__main__':
    app.run(debug=True)
