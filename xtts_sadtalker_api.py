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
base_dir = os.path.dirname(os.path.abspath(__file__))
audio_path = os.path.join(base_dir, "assets", "output.wav")
image_path = os.path.join(base_dir, "assets", "adi2.png")
text_input = "नमस्ते, यह एक डेमो है।"
language = "hi"
voice_sample_path = os.path.join(base_dir, "assets", "adivo.wav")

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
os.chdir(os.path.join(base_dir, "SadTalker"))  # change working dir for SadTalker only
run([
    sys.executable, "inference.py",
    "--driven_audio", audio_path,         # ✅ full path
    "--source_image", image_path,         # ✅ full path
    "--preprocess", "full",
    "--cpu"
])
