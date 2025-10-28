#!/usr/bin/env python3
"""Test that the new few-shot prompts are working correctly."""

import json

# Load first 3 samples
with open("xlcost_cpp_train.json") as f:
    for i in range(3):
        line = f.readline()
        item = json.loads(line)
        
        description = item.get("text") or ""
        reference_code = item.get("code") or ""
        
        # Convert reference code from xlcost format
        reference_code = reference_code.replace(" NEW_LINE ", "\n").replace(" STRNEWLINE ", "\\n")
        
        prompt = f"""Task: {description}

Reference implementation:
{reference_code[:300]}

Write similar C code (only code, no explanations):
"""
        
        print(f"\n{'='*70}")
        print(f"Sample {i}")
        print(f"{'='*70}")
        print(prompt)
        print()
