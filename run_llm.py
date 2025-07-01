import torch
import sys
import json
from transformers import AutoTokenizer, AutoModelForCausalLM

with open("config.json") as f:
    config = json.load(f)
    
device = "cuda:0"

# HuggingFace model path
# Example: "deepseek-ai/deepseek-coder-1.3b-instruct"
model_path = config["MODEL_PATH"]

# Initialize model and tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_path, trust_remote_code=True, torch_dtype=torch.bfloat16).cuda()

text = config["PROMPT"]

# Prompt creation in chat template for Deepseek
prompt = [
          {'role': 'user', 'content' : text}
]

inputs = tokenizer.apply_chat_template(prompt, return_tensors='pt', add_generation_prompt=True).to(model.device)
# tokenizer.eos_token_id is the id of <|EOT|> token

outputs = model.generate(inputs,
                               max_new_tokens=config["max_new_tokens"],
                               do_sample=False,
                               top_k=50,
                               top_p=0.95,
                               num_return_sequences=config["num_return_sequences"],
                               eos_token_id=tokenizer.eos_token_id)


code = tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)


# the above print statement can be modified to directly write to a file, but for
# debugging purposes, it's just printing currently
with open("generated_code/generated_code.c", "w") as f:
    f.write(code)
