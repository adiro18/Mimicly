# Mimicly
An AI-powered web application that generates realistic talking head videos from a single portrait photo and text/PDF inputs using XTTS v2 voice cloning and SadTalker.
Mimicly is a web application that generates realistic talking head videos from a single portrait photo and text or PDF inputs. It combines text-to-speech (TTS) voice cloning with artificial intelligence-driven facial animation.

Key Features
Voice Cloning & TTS (Text-to-Speech)

Uses the advanced multi-lingual XTTS v2 model.
Allows you to upload a short voice sample (.wav) to clone a specific person's voice and generate speech in that voice from any input text.
Facial Animation (SadTalker)

Uses SadTalker to animate a single portrait photo (.png/.jpeg) to match the generated speech.
Generates a natural-looking video where the eyes, mouth, and head movements are synchronized with the cloned audio.
PDF-to-Video Generation

Features a dedicated route to upload a PDF document. It automatically extracts the text from the PDF, synthesizes it into cloned speech, and animates a photo speaking the contents of the document.
Media Library / Gallery

Uses a local SQLite database (mimikly.db) to securely store and retrieve uploaded photos, cloned voice signatures, and generated output videos.
Includes a built-in gallery web interface to view, play, and delete generated videos.
Tech Stack
Frontend: HTML5, CSS3, JavaScript (interactive dashboard, gallery, and generator pages).
Backend: Python, Flask (serves the frontend routes and manages the API endpoints for generation and uploads).
Database: SQLite (handles photo, voice, and video metadata/blobs).
AI Frameworks:
Coqui TTS (XTTS v2) for high-quality voice cloning and speech synthesis.
SadTalker for driven-audio facial animation.
PyTorch (utilizes GPU/CPU acceleration for deep learning models).
PyPDF2 for text extraction from PDF files.
How the Pipeline Works
mermaid
graph TD
    A[User Input: Text/PDF & Photo] --> B[TTS Model: XTTS v2]
    C[Uploaded Voice Sample] --> B
    B -->|Generates Cloned Speech| D[Audio File: output.wav]
    D --> E[SadTalker Model]
    A -->|Source Image| E
    E -->|Animates Face to Match Audio| F[Output Video: .mp4]
    F --> G[SQLite Database & Gallery]
Upload: You upload a portrait photo and a voice sample (.wav) of the target speaker.
Synthesis: You enter text or upload a PDF. The backend runs XTTS v2 using your voice sample to generate a clone of the speaker saying the text.
Animation: The backend passes the generated audio and the uploaded photo to the SadTalker pipeline, which produces the final .mp4 video.
Display: The generated video is saved to the database and appears in your Gallery.
