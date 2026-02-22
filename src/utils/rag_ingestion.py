"""
RAG Ingestion Pipeline — 知识库摄入管道
Load → Clean → Split → Embed → Store (ChromaDB)

使用 sentence-transformers 进行本地嵌入 (Privacy First)
"""

import os
import re
from typing import Optional



class TextSplitterService:
    """
    Service for recursively splitting text into semantic chunks.
    The "Smart Knives" Strategy:
    Priority: Paragraphs > Sentences > Words > Characters.
    """
    def split_text(self, text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
        """
        Splits text using the Recursive Strategy.
        Priority: Paragraphs > Sentences > Words > Characters.
        """
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", " ", ""] # Explicitly define the priority
            )
            
            chunks = splitter.split_text(text)
            print(f"[Split] Original {len(text)} chars -> {len(chunks)} chunks.")
            return chunks
        except ImportError:
            print("Warning: langchain-text-splitters not installed.")
            return [text]


class RAGIngestion:
    """
    知识库摄入管道: Load → Clean → Split → Embed → Store

    每个 Agent 拥有独立的知识库:
      data/{workspace}/{agent}/knowledge_base/  (原始文件)
      data/{workspace}/{agent}/vector_store/    (ChromaDB)
    """

    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_CHUNK_OVERLAP = 50
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 轻量级, ~80MB

    def __init__(self, data_root: str, workspace: str, agent_id: str):
        self.data_root = data_root
        self.workspace = workspace
        self.agent_id = agent_id
        self.kb_path = os.path.join(data_root, workspace, agent_id, "knowledge_base")
        self.vs_path = os.path.join(data_root, workspace, agent_id, "vector_store")
        os.makedirs(self.kb_path, exist_ok=True)
        os.makedirs(self.vs_path, exist_ok=True)

        self._collection = None
        self._embedder = None
        self._splitter_service = TextSplitterService()

    def _get_embedder(self):
        """延迟加载 sentence-transformers 模型"""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(self.EMBEDDING_MODEL)
            except ImportError:
                raise ImportError(
                    "sentence-transformers 未安装。"
                    "请运行: pip install sentence-transformers"
                )
        return self._embedder

    def _get_collection(self):
        """延迟加载 ChromaDB collection"""
        if self._collection is None:
            try:
                import chromadb
                client = chromadb.PersistentClient(path=self.vs_path)
                collection_name = f"{self.agent_id}_knowledge"
                self._collection = client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
            except ImportError:
                raise ImportError(
                    "chromadb 未安装。请运行: pip install chromadb"
                )
        return self._collection

    # ========== Core Pipeline ==========

    def ingest_file(self, file_path: str) -> int:
        """
        处理单个文件: Load → Clean → Split → Embed → Store
        返回生成的 chunk 数
        """
        text = self._load(file_path)
        if not text.strip():
            return 0

        cleaned = self._clean(text)
        
        # Split using the new service
        chunks = self._splitter_service.split_text(
            cleaned, 
            chunk_size=self.DEFAULT_CHUNK_SIZE, 
            chunk_overlap=self.DEFAULT_CHUNK_OVERLAP
        )
        
        self._embed_and_store(chunks, source=os.path.basename(file_path))
        return len(chunks)

    def ingest_all(self) -> dict:
        """
        处理 knowledge_base/ 下所有文件
        返回 {filename: chunk_count}
        """
        results = {}
        if not os.path.exists(self.kb_path):
            return results

        for fname in os.listdir(self.kb_path):
            fpath = os.path.join(self.kb_path, fname)
            if os.path.isfile(fpath):
                try:
                    count = self.ingest_file(fpath)
                    results[fname] = count
                except Exception as e:
                    results[fname] = f"Error: {e}"
        return results

    def query(self, question: str, top_k: int = 5) -> list[dict]:
        """
        检索相关文档片段
        返回 [{content, source, score}]
        """
        collection = self._get_collection()
        embedder = self._get_embedder()

        query_embedding = embedder.encode(question).tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count() or 1)
        )

        docs = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                docs.append({
                    "content": doc,
                    "source": meta.get("source", "unknown"),
                    "score": 1 - distance  # cosine distance → similarity
                })
        return docs

    def rebuild_all(self) -> dict:
        """重建整个知识库索引 (清空 → 重新 ingest)"""
        collection = self._get_collection()
        # 清空集合
        try:
            import chromadb
            client = chromadb.PersistentClient(path=self.vs_path)
            client.delete_collection(f"{self.agent_id}_knowledge")
            self._collection = None  # Force re-creation
        except Exception:
            pass

        results = self.ingest_all()
        return results

    # ========== Sub-steps ==========

    def _load(self, path: str) -> str:
        """Loader Factory: 根据扩展名选择加载器"""
        ext = os.path.splitext(path)[1].lower()

        if ext in (".txt", ".md", ".csv"):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        elif ext in (".doc", ".docx"):
            try:
                import docx
                doc = docx.Document(path)
                return "\n".join(p.text for p in doc.paragraphs)
            except ImportError:
                raise ImportError("python-docx 未安装。请运行: pip install python-docx")

        else:
            # 尝试以文本方式读取
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception:
                return ""

    def _clean(self, text: str) -> str:
        """Auto-Cleaner: 清洗文本"""
        # 1. 多余换行 → 单换行
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 2. 去除页码 (常见格式: "- 1 -", "Page 1", "第 1 页")
        text = re.sub(r"[-–—]\s*\d+\s*[-–—]", "", text)
        text = re.sub(r"Page\s+\d+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"第\s*\d+\s*页", "", text)
        # 3. 去除非打印字符 (保留换行和空格)
        text = re.sub(r"[^\S\n ]+", "", text)
        # 4. 去除多余空格
        text = re.sub(r" {3,}", " ", text)
        return text.strip()

    def _embed_and_store(self, chunks: list[str], source: str) -> None:
        """嵌入并存储到 ChromaDB"""
        if not chunks:
            return

        collection = self._get_collection()
        embedder = self._get_embedder()

        # 生成嵌入
        embeddings = embedder.encode(chunks).tolist()

        # 生成 IDs
        ids = [f"{source}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"source": source, "chunk_index": i} for i in range(len(chunks))]

        # 删除旧的同源文档
        try:
            existing = collection.get(where={"source": source})
            if existing and existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception:
            pass

        # 存入
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )
