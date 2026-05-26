import sys
import torch
import os
from subprocess import run
from TTS.api import TTS
import gc

# Monkey patch
_original_load = torch.load
def patched_load(*args, **kwargs):
    kwargs["weights_only"] = False
    return _original_load(*args, **kwargs)
torch.load = patched_load

# --- CONFIGURATIONS ---
audio_path = r"D:\pro\assets\output.wav"  # ✅ full path
image_path = r"D:\pro\assets\adi2.png"
text_input = "नमस्ते, यह एक डेमो है।"
language = "hi"
voice_sample_path = r"D:\pro\assets\adivo.wav"

# --- STEP 1: TTS Generation ---
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)
tts.tts_to_file(
    text=text_input,
    speaker_wav=voice_sample_path,
    language=language,
    file_path=audio_path
)

# Free memory
torch.cuda.empty_cache()
gc.collect()

# --- STEP 2: SadTalker Execution ---
os.chdir(r"D:\pro\SadTalker")  # change working dir for SadTalker only
run([
    sys.executable, "inference.py",
    "--driven_audio", audio_path,         # ✅ full path
    "--source_image", image_path,         # ✅ full path
    "--preprocess", "full",
    "--cpu"
])
