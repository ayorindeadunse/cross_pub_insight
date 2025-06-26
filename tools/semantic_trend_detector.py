import yaml
from pathlib import Path
from typing import List, Optional
from sentence_transformers import SentenceTransformer, util

class SemanticTrendDetector:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.model_name = self.config["embeddings"]["model_name"]
        self.top_k = self.config["embeddings"]["top_k"]

        self.model = SentenceTransformer(self.model_name)
        self.base_tags = [
            "LangGraph","LangChain", "Crewai", "Vector DB",
            "RAG", "Llama", "OpenAI", "GPT", "Embeddings",
            "Retrieval-Augmented Generation", "Faiss", "ChromaDB", "Weaviate",
            "Retrieval","Fine-tuning","Evaluation","Transformer"
        ]
    
    def _load_config(self, path: str) -> dict:
        with open(Path(path), "r") as f:
            return yaml.safe_load(f)
    
    def detect_trends(
            self,
            text: str,
            additional_candidate_tags: Optional[List[str]] = None
    ) -> List[str]:
        tags = list(set(self.base_tags + (additional_candidate_tags or [])))
        text_embedding = self.model.encode(text, convert_to_tensor=True)
        tag_embeddings = self.model.encode(tags, convert_to_tensor=True)

        similarities = util.pytorch_cos_sim(text_embedding, tag_embeddings)[0]
        top_indices = similarities.topk(self.top_k).indices.tolist()
        return [tags[i] for i in top_indices]



        