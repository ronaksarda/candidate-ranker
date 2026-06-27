import os
from sentence_transformers import SentenceTransformer, CrossEncoder

def download_model():
    print("Downloading all-MiniLM-L6-v2 model for offline use...")
    model_name = "all-MiniLM-L6-v2"
    local_dir = os.path.join(os.path.dirname(__file__), "local_model", model_name)
    
    # Download and cache the model locally
    model = SentenceTransformer(model_name)
    model.save(local_dir)
    print(f"Bi-Encoder successfully saved to {local_dir}")
    
    print("Downloading ms-marco-MiniLM-L-6-v2 Cross-Encoder for offline use...")
    cross_model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    local_cross_dir = os.path.join(os.path.dirname(__file__), "local_model", "ms-marco-MiniLM-L-6-v2")
    
    cross_encoder = CrossEncoder(cross_model_name)
    cross_encoder.save(local_cross_dir)
    print(f"Cross-Encoder successfully saved to {local_cross_dir}")

    print("You can now safely run main.py completely offline.")

if __name__ == "__main__":
    download_model()
