import torch
from huggingface_hub import snapshot_download, hf_hub_download
import json
with open("config.json") as f:
    config = json.load(f)
   
hf_token = config["HUGGINGFACE_TOKEN"]
while True: 
    repo_name = input("Enter the Repository name. : ")
    model_file = input("Enter the LLM file. Leave blank to download the entire repository: ")
    conf = input(
        f"Selected options:\nRepository: {repo_name}; "
        f"Model File: {model_file or '*'}; "
        "Enter Confirm to confirm, or Exit to exit:\n>> "
    )
    if conf == "Exit" or conf == "exit":
        break
    if model_file == "":
        snapshot_download(repo_id=repo_name)
    else:
        hf_hub_download(
            repo_name,
            filename=model_file,
            local_dir='models/',  # Download the model to the "models" folder
            token=hf_token
        )

print("Done")
    
