# eval_config.py
import numpy as np
from deepeval.models import DeepEvalBaseEmbeddingModel
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase, SingleTurnParams
from sentence_transformers import SentenceTransformer


class MultilingualE5Embedding(DeepEvalBaseEmbeddingModel):
    def __init__(self):
        # Mengunduh otomatis (saat run pertama kali) & memuat model lokal E5
        self.model = SentenceTransformer("intfloat/multilingual-e5-large")

    def load_model(self):
        return self.model

    def embed_text(self, text: str) -> list:
        # Menambahkan prefix standar 'query: ' khusus untuk model E5 agar akurat
        return self.model.encode(f"query: {text}").tolist()

    def embed_texts(self, texts: list[str]) -> list[list]:
        return [self.embed_text(t) for t in texts]

    async def a_embed_text(self, text: str) -> list:
        return self.embed_text(text)

    async def a_embed_texts(self, texts: list[str]) -> list[list]:
        return self.embed_texts(texts)

    def get_model_name(self) -> str:
        return "intfloat/multilingual-e5-large"


class SemanticSimilarityMetric(BaseMetric):
    _required_params: list[SingleTurnParams] = [
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.EXPECTED_OUTPUT,
    ]

    def __init__(self, threshold: float = 0.85, model: MultilingualE5Embedding = None):
        self.threshold = threshold
        self.model = model
        self.score = None
        self.reason = None
        self.success = None

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        if self.model is None:
            raise ValueError("Embedding model is not set.")
        actual_embedding = self.model.embed_text(test_case.actual_output)
        expected_embedding = self.model.embed_text(test_case.expected_output)
        
        # Calculate cosine similarity
        dot_product = np.dot(actual_embedding, expected_embedding)
        norm_actual = np.linalg.norm(actual_embedding)
        norm_expected = np.linalg.norm(expected_embedding)
        
        if norm_actual == 0 or norm_expected == 0:
            self.score = 0.0
        else:
            self.score = float(dot_product / (norm_actual * norm_expected))
            
        self.success = self.score >= self.threshold
        self.reason = f"Semantic similarity score of {self.score:.4f} is {'greater' if self.success else 'less'} than threshold {self.threshold}"
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        if self.error is not None:
            self.success = False
        else:
            try:
                self.success = self.score >= self.threshold
            except:
                self.success = False
        return self.success

    @property
    def __name__(self):
        return "Semantic Similarity"