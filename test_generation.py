#!/usr/bin/env python3
"""Quick test of first 5 xlcost samples to verify code generation works."""

import os
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import subprocess
import sys

# Add llvm to path
os.environ['PATH'] = "/scratch/yjb5094/llvm-14/bin:" + os.environ.get('PATH', '')

# Setup
DATA_PATH = "xlcost_cpp_train.json"
CACHE_DIR = "/scratch/yjb5094/hf_cache"
os.makedirs("generated_code", exist_ok=True)

# Load first 5 samples
data = []
with open(DATA_PATH) as f:
    for i, line in enumerate(f):
        if i >= 5:
            break
        if line.strip():
            data.append(json.loads(line))

print(f"✓ Loaded {len(data)} test samples\n")

# Load model
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Loading model on {device}...")
model_name = "deepseek-ai/deepseek-coder-1.3b-instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=CACHE_DIR, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto",
    cache_dir=CACHE_DIR,
    low_cpu_mem_usage=True
)
print("✓ Model loaded\n")

# Test generation on each sample
for sample_idx, item in enumerate(data):
    print(f"{'='*60}")
    print(f"Sample {sample_idx}: {item.get('text', 'N/A')[:80]}")
    print(f"{'='*60}")
    
    prompt = "Write C code (only code, no explanations or comments) to: " + (item.get("text") or "")
    print(f"\nPrompt: {prompt[:100]}...\n")
    
    # Generate
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    print(f"Prompt tokens: {inputs.input_ids.shape[1]}")
    
    with torch.no_grad():
        outputs = model.generate(
            inputs.input_ids,
            max_new_tokens=512,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            early_stopping=True
        )
    
    # Extract generated tokens only
    prompt_token_length = inputs.input_ids.shape[1]
    generated_token_ids = outputs[0][prompt_token_length:]
    generated_code = tokenizer.decode(generated_token_ids, skip_special_tokens=True).strip()
    
    print(f"Generated {len(generated_token_ids)} tokens")
    print(f"\nGenerated code (first 200 chars):")
    print(generated_code[:200])
    print("\n")
    
    # Save to file
    code_file = "generated_code/generated_code.c"
    with open(code_file, "w") as f:
        f.write(generated_code)
    
    # Try cleaning
    print("Running clean_code.py...")
    result = subprocess.run(
        ["python3", "clean_code.py", code_file, "generated_code/clean_code.c"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    
    # Check clean code
    if os.path.exists("generated_code/clean_code.c"):
        with open("generated_code/clean_code.c") as f:
            clean_code = f.read()
        print(f"Clean code ({len(clean_code)} bytes):")
        print(clean_code[:300])
        print("\n")
        
        # Try compiling
        print("Attempting compilation with clang...")
        result = subprocess.run(
            ["clang", "-emit-llvm", "-c", "-g", "generated_code/clean_code.c", "-o", "generated_code/clean_code.bc"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✅ Compilation SUCCEEDED!")
        else:
            print(f"❌ Compilation FAILED:")
            print(result.stderr)
    
    print("\n")

print("✓ Test complete")
