"""知识检索工具 — 基于 TF-IDF 的轻量向量检索，零额外依赖。

从 data/knowledge/ 目录加载 Markdown 攻略文档，
用 TF-IDF 向量化后支持语义检索。
"""

import json
import math
import re
from collections import defaultdict
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "data" / "knowledge"


class TfidfRetriever:
    """轻量 TF-IDF 检索器，无需 chromadb/sentence-transformers。"""

    def __init__(self, knowledge_dir: Path | None = None):
        self._dir = knowledge_dir or KNOWLEDGE_DIR
        self._chunks: list[dict] = []  # [{id, text, source, title}]
        self._idf: dict[str, float] = {}
        self._tfidf_vectors: list[dict[str, float]] = []
        self._loaded = False

    def load(self) -> None:
        """加载知识目录中的所有 Markdown 文档。"""
        if self._loaded:
            return

        for md_file in sorted(self._dir.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            title = md_file.stem
            chunks = self._split_chunks(text, title)
            self._chunks.extend(chunks)

        if not self._chunks:
            self._loaded = True
            return

        # 构建 TF-IDF 向量
        self._build_idf()
        for chunk in self._chunks:
            vec = self._compute_tfidf(chunk["text"])
            self._tfidf_vectors.append(vec)

        self._loaded = True

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        """检索最相关的 k 个文档片段。

        Returns:
            [{score, text, source, title}, ...]
        """
        if not self._loaded:
            self.load()

        if not self._chunks:
            return []

        query_vec = self._compute_tfidf(query)
        scores = []

        for idx, doc_vec in enumerate(self._tfidf_vectors):
            score = self._cosine_sim(query_vec, doc_vec)
            scores.append((score, idx))

        scores.sort(key=lambda x: x[0], reverse=True)
        top_k = scores[:k]

        results = []
        for score, idx in top_k:
            if score < 0.05:  # 相关性太低跳过
                continue
            chunk = self._chunks[idx]
            results.append({
                "score": round(score, 4),
                "text": chunk["text"],
                "source": chunk["source"],
                "title": chunk["title"],
            })

        return results

    # ── 内部方法 ──────────────────────────────────────

    @staticmethod
    def _split_chunks(text: str, source: str) -> list[dict]:
        """按双换行分割文档为 chunks。"""
        chunks = []
        # 先按 ## 标题分割
        sections = re.split(r"\n(?=## )", text)
        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue
            # 提取标题
            title_match = re.match(r"^## (.+)", section)
            title = title_match.group(1) if title_match else ""

            # 每个 section 再按段落分（最大 500 字）
            paragraphs = section.split("\n\n")
            buffer = ""
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                if len(buffer) + len(para) < 500:
                    buffer += "\n" + para if buffer else para
                else:
                    if buffer:
                        chunks.append({"text": buffer.strip(), "source": source, "title": title})
                    buffer = para
            if buffer:
                chunks.append({"text": buffer.strip(), "source": source, "title": title})

        return chunks

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """简单中文分词：按汉字、英文单词、数字切分。"""
        # 中文按字切，英文按词切
        tokens = re.findall(r"[\u4e00-\u9fff]|[a-zA-Z]+|\d+", text.lower())
        # 过滤单字停用词
        return [t for t in tokens if len(t) > 1 or t.isdigit()]

    def _build_idf(self) -> None:
        """构建 IDF 字典。"""
        df = defaultdict(int)
        N = len(self._chunks)

        for chunk in self._chunks:
            unique_tokens = set(self._tokenize(chunk["text"]))
            for token in unique_tokens:
                df[token] += 1

        self._idf = {
            token: math.log((N + 1) / (count + 1)) + 1
            for token, count in df.items()
        }

    def _compute_tfidf(self, text: str) -> dict[str, float]:
        """计算文本的 TF-IDF 向量。"""
        tokens = self._tokenize(text)
        tf = defaultdict(float)
        for token in tokens:
            tf[token] += 1

        # 归一化 TF
        max_tf = max(tf.values()) if tf else 1
        vec = {}
        for token, count in tf.items():
            if token in self._idf:
                vec[token] = (count / max_tf) * self._idf[token]

        return vec

    @staticmethod
    def _cosine_sim(a: dict[str, float], b: dict[str, float]) -> float:
        """计算两个稀疏向量的余弦相似度。"""
        if not a or not b:
            return 0.0

        dot = sum(a.get(k, 0) * b.get(k, 0) for k in set(a) & set(b))
        norm_a = math.sqrt(sum(v ** 2 for v in a.values()))
        norm_b = math.sqrt(sum(v ** 2 for v in b.values()))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# 单例
_retriever: TfidfRetriever | None = None


def get_retriever() -> TfidfRetriever:
    """获取全局检索器实例。"""
    global _retriever
    if _retriever is None:
        _retriever = TfidfRetriever()
        _retriever.load()
    return _retriever


async def retrieve_knowledge(query: str, k: int = 3) -> list[dict]:
    """异步检索知识库。

    Args:
        query: 用户查询字符串
        k: 返回结果数

    Returns:
        [{score, text, source, title}, ...]
    """
    retriever = get_retriever()
    return retriever.retrieve(query, k=k)
