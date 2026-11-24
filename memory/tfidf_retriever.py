import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, Optional


@dataclass
class RetrievedEvidence:
    doc_id: str
    category: str
    title: str
    snippet: str
    score: float
    matched_terms: List[str]
    metadata: Dict[str, Any]

    def summary(self) -> str:
        matched = ", ".join(self.matched_terms[:5]) if self.matched_terms else "general match"
        return f"[{self.category.upper()}] '{self.title}' (Score: {self.score:.4f} | Terms: {matched})"


class TFIDFRetriever:

    STOP_WORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
        "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
        "but", "by", "can", "can't", "cannot", "could", "did", "do", "does", "doing", "don't", "down",
        "during", "each", "few", "for", "from", "further", "had", "has", "have", "having", "he", "her",
        "here", "hers", "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is",
        "isn't", "it", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no",
        "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "out",
        "over", "own", "same", "shan't", "she", "should", "so", "some", "such", "than", "that", "the",
        "their", "theirs", "them", "themselves", "then", "there", "these", "they", "this", "those",
        "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "were", "what",
        "when", "where", "which", "while", "who", "whom", "why", "with", "won't", "would", "you", "your"
    }

    def __init__(self):
        self.documents: List[Dict[str, Any]] = []
        self.doc_term_frequencies: List[Dict[str, float]] = []
        self.doc_lengths: List[float] = []
        self.idf: Dict[str, float] = {}
        self.vocabulary: set = set()
        self.total_docs: int = 0

    def tokenize(self, text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower())
        return [w for w in words if w not in self.STOP_WORDS]

    def fit(self, documents: List[Dict[str, Any]]) -> "TFIDFRetriever":

        self.documents = documents
        self.total_docs = len(documents)
        self.doc_term_frequencies = []
        self.doc_lengths = []
        self.vocabulary = set()

        if self.total_docs == 0:
            self.idf = {}
            return self

        doc_word_sets: List[set] = []

        for doc in documents:
            text = f"{doc.get('title', '')} {doc.get('content', '')}"
            tokens = self.tokenize(text)
            term_counts = Counter(tokens)
            total_tokens = len(tokens) if tokens else 1

            tf = {t: count / total_tokens for t, count in term_counts.items()}
            self.doc_term_frequencies.append(tf)
            self.vocabulary.update(term_counts.keys())
            doc_word_sets.append(set(term_counts.keys()))

        self.idf = {}
        for term in self.vocabulary:
            df = sum(1 for d_words in doc_word_sets if term in d_words)
            self.idf[term] = math.log(1.0 + (self.total_docs / (1.0 + df))) + 1.0

        for tf in self.doc_term_frequencies:
            sq_sum = 0.0
            for term, tf_val in tf.items():
                tfidf_val = tf_val * self.idf.get(term, 1.0)
                sq_sum += tfidf_val * tfidf_val
            self.doc_lengths.append(math.sqrt(sq_sum) if sq_sum > 0 else 1.0)

        return self

    def query(self, query_text: str, top_k: int = 3) -> List[RetrievedEvidence]:
        """
        Compute sparse TF-IDF query vector and evaluate Cosine Similarity:
        cos(q, d) = (q . d) / (||q|| * ||d||)
        Returns top_k ranked documents with match attribution.
        """
        if self.total_docs == 0:
            return []

        q_tokens = self.tokenize(query_text)
        if not q_tokens:
            return []

        q_counts = Counter(q_tokens)
        q_len_tokens = len(q_tokens)

        q_vec: Dict[str, float] = {}
        q_sq_sum = 0.0
        for term, count in q_counts.items():
            if term in self.idf:
                tf_q = count / q_len_tokens
                val = tf_q * self.idf[term]
                q_vec[term] = val
                q_sq_sum += val * val

        q_norm = math.sqrt(q_sq_sum)
        if q_norm == 0.0:
            return []

        scores: List[Tuple[int, float, List[str]]] = []

        for idx, tf_d in enumerate(self.doc_term_frequencies):
            dot_product = 0.0
            matched_terms = []
            for term, q_val in q_vec.items():
                if term in tf_d:
                    d_val = tf_d[term] * self.idf[term]
                    dot_product += q_val * d_val
                    matched_terms.append(term)

            d_norm = self.doc_lengths[idx]
            similarity = dot_product / (q_norm * d_norm) if (q_norm * d_norm) > 0 else 0.0

            if similarity > 0.0:
                scores.append((idx, similarity, matched_terms))

        scores.sort(key=lambda x: x[1], reverse=True)

        results: List[RetrievedEvidence] = []
        for idx, score, matched in scores[:top_k]:
            doc = self.documents[idx]
            content = doc.get("content", "")
            snippet = content[:180] + "..." if len(content) > 180 else content
            results.append(
                RetrievedEvidence(
                    doc_id=str(doc.get("id", f"doc-{idx}")),
                    category=doc.get("category", "policy"),
                    title=doc.get("title", "Untitled Document"),
                    snippet=snippet,
                    score=round(score, 4),
                    matched_terms=matched,
                    metadata=doc.get("metadata", {})
                )
            )

        return results
