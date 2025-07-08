import yaml
from pathlib import Path
from collections import defaultdict
from typing import List, Optional, Union
from sentence_transformers import SentenceTransformer, util

CATEGORY_MAP = {
    "LangGraph": "Frameworks",
    "LangChain": "Frameworks",
    "Crewai": "Frameworks",
    "Faiss": "Vector DBs",
    "ChromaDB": "Vector DBs",
    "Weaviate": "Vector DBs",
    "Llama": "LLMs",
    "GPT": "LLMs",
    "OpenAI": "LLMs",
    "Retrieval": "Techniques",
    "RAG": "Techniques",
    "Evaluation": "Workflows",
    "Fine-tuning": "Workflows",
    }

class SemanticTrendDetector:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.model_name = self.config["embeddings"]["model_name"]
        self.top_k = self.config["embeddings"]["top_k"]
        self.score_threshold = self.config["embeddings"].get("score_threshold", 0.25)

        self.model = SentenceTransformer(self.model_name)
        self.base_tags = [
            "LangGraph","LangChain", "Crewai", "Vector DB",
            "RAG", "Llama", "OpenAI", "GPT", "Embeddings",
            "Retrieval-Augmented Generation", "Faiss", "ChromaDB", "Weaviate",
            "Retrieval","Fine-tuning","Evaluation","Transformer"
        ]
    
    def _load_config(self, path: str) -> dict:
        try:
            with open(Path(path), "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Error loading config from {path}: {e}")

    def detect_trends(
        self,
        text: str,
        additional_candidate_tags: Optional[List[str]] = None,
        score_threshold: Optional[float] = None,
        return_scores: bool = False
    ) -> Union[List[str], List[tuple]]:
        tags = list(set(self.base_tags + (additional_candidate_tags or [])))
        text_embedding = self.model.encode(text, convert_to_tensor=True)
        tag_embeddings = self.model.encode(tags, convert_to_tensor=True)

        similarities = util.pytorch_cos_sim(text_embedding, tag_embeddings)[0]
        scored_tags = list(zip(tags, similarities.tolist()))

        threshold = score_threshold if score_threshold is not None else self.score_threshold
        filtered = [(tag, score) for tag, score in scored_tags if score >= threshold]
        sorted_filtered = sorted(filtered, key=lambda x: x[1], reverse=True)

        # 🔍 Log matches
        print("\n[DEBUG] Trend Detector Matches:")
        for tag, score in sorted_filtered:
            print(f"  - {tag} ({score:.3f})")

        if return_scores:
            return sorted_filtered
        else:
            return [tag for tag, _ in sorted_filtered]

    @staticmethod
    def group_by_category(tags: list[str]) -> str:
        grouped = defaultdict(list)
        for tag in tags:
            category = CATEGORY_MAP.get(tag, "Other")
            grouped[category].append(tag)
    
        result_lines = []
        for category, items in grouped.items():
            result_lines.append(f"{category}: {', '.join(items)}")
    
        return "\n".join(result_lines)




        