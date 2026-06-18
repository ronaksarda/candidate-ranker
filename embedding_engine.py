import os
import numpy as np
from sentence_transformers import SentenceTransformer

class EmbeddingEngine:
    def __init__(self, model_path=None):
        if model_path is None:
            local_path = os.path.join(os.path.dirname(__file__), "local_model", "all-MiniLM-L6-v2")
            if os.path.isdir(local_path):
                model_path = local_path
            else:
                # Fallback: download from HuggingFace (for Colab / first run)
                model_path = "all-MiniLM-L6-v2"
            
        self.model = SentenceTransformer(model_path, device='cpu')
        
        # Define JD Facets text
        self.facets_text = {
            "core_ml": (
                "Production experience with embeddings-based retrieval systems, sentence-transformers, search systems, "
                "ranking evaluation like NDCG, MRR, MAP. Pre-LLM ML production experience in NLP and IR. "
                "Strong scrappy product-engineering attitude, able to ship end-to-end working rankers."
            ),
            "engineering_infra": (
                "Production experience with vector databases or hybrid search infrastructure such as Pinecone, "
                "Weaviate, Qdrant, Milvus, OpenSearch, FAISS. Strong Python skills and code quality. "
                "Experience dealing with embedding drift, index refresh, and large-scale deployment."
            ),
            "nice_to_haves": (
                "LLM fine-tuning experience like LoRA, QLoRA, PEFT. Learning-to-rank models, XGBoost, neural rankers. "
                "Prior exposure to HR-tech, recruiting tech, or marketplace products. "
                "Distributed systems, large-scale inference optimization, and open-source contributions."
            )
        }
        
        # Pre-compute facet embeddings
        facet_texts = [self.facets_text["core_ml"], self.facets_text["engineering_infra"], self.facets_text["nice_to_haves"]]
        facet_embeddings = self.model.encode(facet_texts, normalize_embeddings=True)
        self.facet_vectors = {
            "core_ml": facet_embeddings[0],
            "engineering_infra": facet_embeddings[1],
            "nice_to_haves": facet_embeddings[2]
        }
        
    def batch_encode(self, texts, batch_size=256):
        """
        Encodes a list of texts into normalized embeddings.
        """
        # normalize_embeddings=True allows dot product instead of full cosine similarity
        return self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
        
    def compute_similarity(self, candidate_embeddings):
        """
        Computes weighted similarity for a batch of candidate embeddings against JD facets.
        Returns array of similarity scores.
        """
        # Weights: core_ml: 45%, engineering_infra: 45%, nice_to_haves: 10%
        # Or more simply, w1=0.45, w2=0.45, w3=0.1
        w_core = 0.45
        w_eng = 0.45
        w_nice = 0.10
        
        # candidate_embeddings is (N, dim)
        # dot product with each facet vector (dim,) -> (N,)
        score_core = np.dot(candidate_embeddings, self.facet_vectors["core_ml"])
        score_eng = np.dot(candidate_embeddings, self.facet_vectors["engineering_infra"])
        score_nice = np.dot(candidate_embeddings, self.facet_vectors["nice_to_haves"])
        
        return (w_core * score_core) + (w_eng * score_eng) + (w_nice * score_nice)
