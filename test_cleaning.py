#!/usr/bin/env python3
"""
Test the code cleaning logic independently to verify it's not the bottleneck.
"""

import json
import subprocess
import os
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

def test_cleaning_on_prompt(prompt_idx):
    """Generate code for a prompt and test if cleaning + compilation works."""
    
    with open("QuestionPromptForLLMs.json") as f:
        data = json.load(f)["questions"]
    
    q = data[prompt_idx]
    
    # Generate code
    model_name = "deepseek-ai/deepseek-coder-1.3b-instruct"
    cache_dir = "/scratch/yjb5094/hf_cache"
    
    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        cache_dir=cache_dir,
        low_cpu_mem_usage=True
    )
    
    prompt = "Write C code (only code, no explanations or comments) to: " + q['task']
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id
        )
    
    code = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    print(f"\n{'='*70}")
    print(f"PROMPT {prompt_idx}: {q['title']}")
    print(f"{'='*70}")
    print(f"Generated code length: {len(code)} chars")
    print(f"First 300 chars of generated code:")
    print(code[:300])
    print("\n---\n")
    
    # Save raw generated code
    os.makedirs("generated_code", exist_ok=True)
    with open("generated_code/generated_code.c", "w") as f:
        f.write(code)
    
    # Run the cleaning script
    result = subprocess.run(["bash", "analyze_only.sh"], capture_output=True, text=True, timeout=120)
    
    # Check if it compiled
    compiled = os.path.exists("generated_code/clean_code.out")
    
    print(f"\nCleaning output (last 15 lines):")
    for line in result.stdout.split("\n")[-15:]:
        if line.strip():
            print(f"  {line}")
    
    if result.returncode != 0 and result.stderr:
        print(f"\nCleaning script STDERR (last 10 lines):")
        for line in result.stderr.split("\n")[-10:]:
            if line.strip():
                print(f"  {line}")
    
    # Show cleaned code
    if os.path.exists("generated_code/clean_code.c"):
        with open("generated_code/clean_code.c") as f:
            cleaned = f.read()
        print(f"\nCleaned code length: {len(cleaned)} chars")
        print(f"First 400 chars of cleaned code:")
        print(cleaned[:400])
        print(f"\nLast 200 chars of cleaned code:")
        print(cleaned[-200:])
    
    print(f"\nRESULT: {'✓ COMPILED' if compiled else '✗ FAILED TO COMPILE'}")
    print(f"{'='*70}\n")
    
    return compiled

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Test specific prompts
        prompts = [int(x) for x in sys.argv[1:]]
    else:
        # Test all
        prompts = list(range(23))
    
    results = {}
    for idx in prompts:
        try:
            compiled = test_cleaning_on_prompt(idx)
            results[idx] = compiled
        except Exception as e:
            print(f"ERROR on prompt {idx}: {e}")
            results[idx] = False
    
    print(f"\n\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    compiled = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Compilation rate: {compiled}/{total} ({100*compiled/total:.1f}%)")
    print(f"\nCompiled: {[i for i, v in results.items() if v]}")
    print(f"Failed:   {[i for i, v in results.items() if not v]}")
