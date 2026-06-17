import os
from sentence_transformers import SentenceTransformer

def download_model():
    print("Downloading all-MiniLM-L6-v2 model for offline use...")
    model_name = "all-MiniLM-L6-v2"
    local_dir = os.path.join(os.path.dirname(__file__), "local_model", model_name)
    
    # Download and cache the model locally
    model = SentenceTransformer(model_name)
    model.save(local_dir)
    print(f"Model successfully saved to {local_dir}")
    print("You can now safely run main.py completely offline.")

if __name__ == "__main__":
    download_model()
