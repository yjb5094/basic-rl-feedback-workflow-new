import os
import json
import csv
import subprocess
import shutil
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import time

# ------------------- Helper Functions -------------------
def auto_commit(completed_count, model_name):
    """Auto-commit results and logs every 30 samples"""
    if completed_count % 30 == 0 and completed_count > 0:
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=os.getcwd(),
                check=False,
                timeout=10
            )
            subprocess.run(
                ["git", "commit", "-m", f"Auto-save: Completed {completed_count} samples with {model_name}"],
                cwd=os.getcwd(),
                check=False,
                timeout=10
            )
            print(f"  💾 Auto-saved to git (checkpoint: {completed_count} samples)")
        except Exception as e:
            print(f"  ⚠️ Auto-commit failed: {e}")

# ------------------- Configuration -------------------
DATA_PATH = "xlcost_cpp_train.json"  # xlcost dataset (JSONL format)
CACHE_DIR = "/scratch/yjb5094/hf_cache"
RESULTS_FILE = "xlcost_results.csv"
CODEQL_LOG_FILE = "feedback/codeql_errors_xlcost.txt"  # Separate log for xlcost
MODELS = ["deepseek-ai/deepseek-coder-1.3b-instruct"]
MAX_PROMPTS = 463  # Total prompts in xlcost dataset
MAX_TOKENS = 512
BATCH_SIZE = 4  # Adjust based on GPU memory
ANALYSIS_SCRIPT = "analyze_only.sh"

# ------------------- Load dataset -------------------
# Load JSONL format (one JSON object per line)
data = []
print(f"Loading {DATA_PATH}...")
try:
    with open(DATA_PATH) as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    print(f"✓ Loaded {len(data)} samples from xlcost dataset")
except FileNotFoundError:
    print(f"✗ Error: {DATA_PATH} not found!")
    print(f"  Available files: {os.listdir('.')}")
    exit(1)

# Track completed prompts
done = set()
if os.path.exists(RESULTS_FILE):
    with open(RESULTS_FILE) as f:
        for row in csv.reader(f):
            if len(row) >= 2:
                done.add((row[0], int(row[1])))
    print(f"✓ Resuming from {len(done)} completed prompts")

# Ensure directories exist
os.makedirs("generated_code", exist_ok=True)
os.makedirs("feedback", exist_ok=True)

# Clear previous CodeQL error log
with open(CODEQL_LOG_FILE, "w") as log:
    log.write("==== Aggregated CodeQL Error Log - XLCost ====\n\n")

start_time = time.time()

for model_name in MODELS:
    print(f"\n=== Loading model: {model_name} ===")
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
    print(f"Model is on device: {model.device}")
    print("✓ Model loaded successfully.\n")

    completed = 0
    model_start = time.time()

    # ------------------- Batched generation -------------------
    for batch_start in range(0, min(MAX_PROMPTS, len(data)), BATCH_SIZE):
        batch_items = data[batch_start: batch_start + BATCH_SIZE]
        batch_prompts = [
            "Write C code (only code, no explanations or comments) to: " + (item.get("text") or item.get("prompt") or item.get("question") or item.get("instruction") or "")
            for item in batch_items
        ]

        # Skip prompts that are already done
        skip_indices = [
            i for i, item in enumerate(batch_items)
            if (model_name, batch_start + i) in done
        ]
        if len(skip_indices) == len(batch_items):
            continue

        try:
            # Tokenize batch
            inputs = tokenizer(batch_prompts, padding=True, return_tensors="pt").to(model.device)

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=MAX_TOKENS,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id,
                    early_stopping=True
                )

            # Decode each output and process
            for i, output_ids in enumerate(outputs):
                prompt_index = batch_start + i
                if (model_name, prompt_index) in done:
                    continue  # Already processed

                code = tokenizer.decode(output_ids, skip_special_tokens=True)

                # Save generated code
                code_file = "generated_code/generated_code.c"
                with open(code_file, "w") as f:
                    f.write(code)

                # Run analysis
                # Run canonical analysis script and mirror run_pipeline.sh semantics
                try:
                    result = subprocess.run(
                        ["bash", ANALYSIS_SCRIPT],
                        check=False,
                        timeout=300
                    )

                    # compile_ok mirrors pipeline's bitcode generation success
                    compile_ok = os.path.exists("generated_code/clean_code.bc") and result.returncode == 0
                    if not compile_ok:
                        print(f"  ⚠️  Compilation/bitcode generation failed for prompt #{prompt_index}")
                except subprocess.TimeoutExpired:
                    print(f"  ⏱️ Analysis timeout for prompt #{prompt_index}")
                    compile_ok = False

                # KLEE check for SEMANTIC ERRORS (runtime memory safety issues)
                # semantic_err = True iff KLEE produced any .err files in klee_output
                semantic_err = False
                if os.path.exists("klee_output"):
                    try:
                        files = os.listdir("klee_output")
                        semantic_err = any(f.endswith(".err") for f in files)
                    except Exception:
                        semantic_err = False

                # CodeQL check for SECURITY ERRORS (static analysis vulnerabilities)
                feedback_file = "feedback/codeql_feedback.txt"
                security_err = False
                if os.path.exists(feedback_file):
                    try:
                        with open(feedback_file, 'r') as f:
                            content = f.read().strip()
                        
                        # Security error found if file has content AND it's not the dummy message
                        if content and "CodeQL analysis completed" not in content:
                            security_err = True
                        
                        # Log all non-dummy findings
                        if security_err:
                            with open(CODEQL_LOG_FILE, "a") as log:
                                log.write(f"\n--- Prompt #{prompt_index} ({model_name}) ---\n")
                                log.write(content)
                                log.write("\n--------------------------------------------\n")
                    except IOError as e:
                        print(f"  ⚠️ Error reading CodeQL feedback: {e}")
                        security_err = False
                else:
                    # Feedback file doesn't exist - this shouldn't happen if analyze_only.sh ran correctly
                    print(f"  ⚠️ Warning: CodeQL feedback file not found for prompt #{prompt_index}")

                # Save results
                with open(RESULTS_FILE, "a") as out:
                    out.write(f"{model_name},{prompt_index},{compile_ok},{semantic_err},{security_err}\n")

                completed += 1

                # Progress tracking every 50 prompts
                if completed % 50 == 0:
                    elapsed = time.time() - model_start
                    if completed > 0:
                        avg_time = elapsed / completed
                        remaining = max(0, (MAX_PROMPTS - prompt_index)) * avg_time
                        eta_hours = remaining / 3600
                        print(f"\n  📊 Progress: {completed}/{MAX_PROMPTS}")
                        print(f"  ⏱️ Avg time per prompt: {avg_time:.1f}s")
                        print(f"  ⏱️ ETA: {eta_hours:.2f} hours\n")
                    else:
                        print(f"\n  📊 Progress: {completed}/{MAX_PROMPTS} (no completed prompts yet)\n")

        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                print("💥 GPU OOM! Consider reducing BATCH_SIZE or MAX_TOKENS")
                torch.cuda.empty_cache()
                time.sleep(2)
                continue
        except Exception as e:
            print(f"✗ Error in batch starting at {batch_start}: {e}")
            continue

    model_elapsed = time.time() - model_start
    print(f"\n{'='*60}")
    print(f"✓ {model_name} complete! Completed: {completed}/{MAX_PROMPTS}")
    print(f"  Time: {model_elapsed/3600:.2f} hours")
    if completed > 0:
        print(f"  Avg per prompt: {model_elapsed/completed:.1f}s")
    else:
        print("  Avg per prompt: N/A (no completed prompts)")
    print(f"{'='*60}\n")

    del model, tokenizer
    torch.cuda.empty_cache()
    time.sleep(3)

total_time = time.time() - start_time
print(f"\n🎉 All models processed successfully!")
print(f"Total time: {total_time/3600:.2f} hours")
print(f"Results saved to: {RESULTS_FILE}")
print(f"Aggregated CodeQL errors saved to: {CODEQL_LOG_FILE}")
