import os
import numpy as np


class EmbeddingEngine:
    def __init__(self, model_path=None):
        if model_path is None:
            local_path = os.path.join(os.path.dirname(__file__), "local_model", "all-MiniLM-L6-v2")
            if os.path.isdir(local_path):
                model_path = local_path
            else:
                model_path = "all-MiniLM-L6-v2"

        # Direct Transformers/Torch inference keeps the same local MiniLM model and
        # mean-pooling behavior, but avoids SentenceTransformer's slower startup path.
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        try:
            torch.set_num_threads(min(8, os.cpu_count() or 4))
        except RuntimeError:
            pass

        self.tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=os.path.isdir(model_path))
        self.model = AutoModel.from_pretrained(model_path, local_files_only=os.path.isdir(model_path))
        self.model.eval()

        self.facets_text = {
            "core_ml": (
                "Built and shipped embedding-based retrieval pipelines handling millions of queries. "
                "Integrated sentence-transformers, BGE, and OpenAI embeddings into production search infrastructure. "
                "Monitored NDCG and MRR in A/B tests to improve offline-to-online correlation. "
                "Scaled hybrid retrieval architectures and managed index refresh and embedding drift."
            ),
            "engineering_infra": (
                "Deployed and maintained production vector databases like Pinecone, Weaviate, Qdrant, Milvus, and FAISS. "
                "Wrote clean, production-grade Python for large-scale distributed systems. "
                "Architected scalable infrastructure for candidate-JD matching and semantic search. "
                "Managed latency, throughput, and index optimization for real-time retrieval."
            ),
            "nice_to_haves": (
                "Fine-tuned LLMs using LoRA, QLoRA, and PEFT for domain-specific tasks. "
                "Trained learning-to-rank models using XGBoost and neural rankers. "
                "Built marketplace products and talent intelligence features in the HR-tech space. "
                "Contributed to open-source AI projects and mentored junior engineers on the team."
            )
        }

        facet_texts = [
            self.facets_text["core_ml"],
            self.facets_text["engineering_infra"],
            self.facets_text["nice_to_haves"],
        ]
        facet_embeddings = self.batch_encode(facet_texts, batch_size=3)
        self.facet_vectors = {
            "core_ml": facet_embeddings[0],
            "engineering_infra": facet_embeddings[1],
            "nice_to_haves": facet_embeddings[2],
        }

    def batch_encode(self, texts, batch_size=256):
        """
        Encodes text into normalized all-MiniLM-L6-v2 sentence embeddings.
        """
        torch = self.torch
        vectors = []
        with torch.inference_mode():
            for start in range(0, len(texts), batch_size):
                batch = texts[start:start + batch_size]
                encoded = self.tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=256,
                    return_tensors="pt",
                )
                output = self.model(**encoded).last_hidden_state
                mask = encoded["attention_mask"].unsqueeze(-1).expand(output.size()).float()
                pooled = (output * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
                pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
                vectors.append(pooled.cpu().numpy())
        return np.vstack(vectors) if vectors else np.empty((0, 384), dtype=np.float32)

    def compute_similarity(self, candidate_embeddings):
        """
        Computes weighted similarity for a batch of candidate embeddings against JD facets.
        Returns array of similarity scores.
        """
        w_core = 0.45
        w_eng = 0.45
        w_nice = 0.10

        score_core = np.dot(candidate_embeddings, self.facet_vectors["core_ml"])
        score_eng = np.dot(candidate_embeddings, self.facet_vectors["engineering_infra"])
        score_nice = np.dot(candidate_embeddings, self.facet_vectors["nice_to_haves"])

        return (w_core * score_core) + (w_eng * score_eng) + (w_nice * score_nice)
