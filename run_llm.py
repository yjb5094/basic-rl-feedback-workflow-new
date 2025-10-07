import torch
import sys
import json
import os
import tempfile
import shutil
from transformers import AutoTokenizer, AutoModelForCausalLM

# Set cache directory to /scratch/$whoami
cache_dir = f"/scratch/{os.getlogin()}/hf_cache"
os.makedirs(cache_dir, exist_ok=True)
print(f"Using cache directory: {cache_dir}")

# Set all HuggingFace cache environment variables to scratch directory
os.environ['HF_HOME'] = cache_dir
os.environ['TRANSFORMERS_CACHE'] = cache_dir
os.environ['HF_DATASETS_CACHE'] = cache_dir
os.environ['HF_HUB_CACHE'] = cache_dir

with open("config.json", "r") as f:
    config = json.load(f)

# Create output directory
os.makedirs("generated_code", exist_ok=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

model_path = config["MODEL_PATH"]
text = config["PROMPT"]

print(f"Loading model: {model_path}")

# Initialize tokenizer with explicit cache directory
tokenizer = AutoTokenizer.from_pretrained(
    model_path, 
    trust_remote_code=True,
    cache_dir=cache_dir,
    local_files_only=False
)

# Add padding token if it doesn't exist
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# Initialize model with explicit cache directory
if device == "cuda":
    model = AutoModelForCausalLM.from_pretrained(
        model_path, 
        trust_remote_code=True, 
        dtype=torch.float16,
        cache_dir=cache_dir,
        local_files_only=False,
        use_safetensors=True
    ).cuda()
else:
    model = AutoModelForCausalLM.from_pretrained(
        model_path, 
        trust_remote_code=True,
        cache_dir=cache_dir,
        local_files_only=False,
        use_safetensors=True
    )

print(f"Model loaded successfully on {device}")

# Simple text prompt for base models
prompt_text = f"// {text}\n#include <stdio.h>\n\nint main() {{\n"

inputs = tokenizer(prompt_text, return_tensors='pt').to(model.device)

print("Generating code...")
outputs = model.generate(
    inputs.input_ids,
    max_new_tokens=config["max_new_tokens"],
    do_sample=True,
    temperature=0.7,
    top_k=50,
    top_p=0.95,
    num_return_sequences=config["num_return_sequences"],
    eos_token_id=tokenizer.eos_token_id,
    pad_token_id=tokenizer.eos_token_id
)

# Decode the full generated text
generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

# Extract just the new content (remove the prompt)
code = generated_text[len(prompt_text):].strip()

# Add the full program structure
full_code = f"{prompt_text}{code}"

print("Code generated successfully!")

# Write to file
with open("generated_code/generated_code.c", "w") as f:
    f.write(full_code)

print(f"Code saved to: generated_code/generated_code.c")

# Clean up cache directory
print("Cleaning up cache...")
try:
    shutil.rmtree(cache_dir)
    print("Cache cleanup complete")
except Exception as e:
    print(f"Warning: Could not clean up cache directory: {e}")
