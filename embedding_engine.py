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
                "I have shipped embedding-based retrieval pipelines to real users at production scale. "
                "I used NDCG, MRR, and MAP to measure quality and ran extensive A/B tests to compare retrieval architectures. "
                "In production, I actively handled embedding drift, managed index refreshes, and built robust hybrid BM25+dense pipelines. "
                "I utilized sentence-transformers, BGE, E5, and OpenAI embeddings for real-time semantic search. "
                "I operated a cross-encoder reranker in production and rigorously designed offline-to-online evaluation correlations."
            ),
            "engineering_infra": (
                "I have operated vector databases like Pinecone, Weaviate, Qdrant, Milvus, FAISS, and OpenSearch at production scale. "
                "I systematically managed index latency, throughput, and system reliability for real-time serving of embedding models. "
                "I built highly scalable candidate-JD and document retrieval infrastructure from scratch. "
                "I write clean, production-grade Python to architect and deploy distributed ML systems. "
                "I have deep operational experience dealing with ANN index tuning, including HNSW parameters, IVF, and quantization."
            ),
            "nice_to_haves": (
                "I have hands-on experience fine-tuning LLMs using LoRA, QLoRA, and PEFT. "
                "I trained and deployed learning-to-rank models utilizing XGBoost and neural rankers. "
                "I have strong 0-to-1 product build experience, specifically within HR-tech and marketplace product domains. "
                "I am an active contributor to open-source ML projects and have a proven track record of mentoring junior engineers."
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
