import sqlite3
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

class ChromaStore:
    """Wrapper around ChromaDB PersistentClient for storing and querying text embeddings."""

    def __init__(self, persist_dir: str = "logs/chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection("agent_memory")

    def add(self, text: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None, doc_id: Optional[str] = None):
        import uuid
        self.collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata or {}],
            ids=[doc_id or str(uuid.uuid4())]
        )

    def query(self, embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=limit
        )
        output = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
            distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)
            for d, m, dist in zip(docs, metas, distances):
                # Convert distance to similarity score
                output.append({
                    "text": d,
                    "metadata": m,
                    "score": float(1.0 / (1.0 + dist))
                })
        return output


class MemoryIndex:
    """Manages structured context storage in SQLite and semantic vector indexing using embeddings (ChromaDB or NumPy fallback)."""

    def __init__(self, db_path: str = "logs/memory.db", client: Optional[Any] = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.client = client
        self._init_db()

        # Initialize Chroma if available
        self.chroma_store = None
        if CHROMA_AVAILABLE:
            try:
                chroma_dir = str(self.db_path.parent / "chroma_db")
                self.chroma_store = ChromaStore(persist_dir=chroma_dir)
            except Exception:
                self.chroma_store = None

    def _init_db(self):
        """Initializes SQLite tables for messages history and semantic embeddings (fallback)."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Structured context storage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                tool_calls TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Fallback embeddings table when Chroma is unavailable
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                vector TEXT,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def store_message(self, session_id: str, role: str, content: Optional[str], tool_calls: Optional[List[Dict[str, Any]]] = None):
        """Stores a chat message in the SQLite database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, role, content, tool_calls) VALUES (?, ?, ?, ?)",
            (session_id, role, content, json.dumps(tool_calls) if tool_calls else None)
        )
        conn.commit()
        conn.close()

    def load_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Loads message history from SQLite for a session."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, tool_calls FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
        messages = []
        for r in rows:
            msg = {
                "role": r["role"],
                "content": r["content"]
            }
            if r["tool_calls"]:
                msg["tool_calls"] = json.loads(r["tool_calls"])
            messages.append(msg)
        conn.close()
        return messages

    def clear_session(self, session_id: str):
        """Deletes all stored message logs for a session from SQLite."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

    def store_embedding(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Generates a text vector embedding and persists it semantically."""
        if not text or not self.client:
            return

        try:
            vector = self.client.get_embedding(text)

            if self.chroma_store:
                # Add to ChromaDB
                self.chroma_store.add(text, vector, metadata)
            else:
                # Fallback to SQLite table
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO embeddings (text, vector, metadata) VALUES (?, ?, ?)",
                    (text, json.dumps(vector), json.dumps(metadata) if metadata else None)
                )
                conn.commit()
                conn.close()
        except Exception:
            pass

    def search_semantic(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Searches memory semantically. Uses ChromaDB, falling back to NumPy cosine similarity."""
        if not query or not self.client:
            return []

        try:
            vector = self.client.get_embedding(query)

            if self.chroma_store:
                return self.chroma_store.query(vector, limit)

            # Fallback cosine-similarity search using NumPy
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT text, vector, metadata FROM embeddings")
            rows = cursor.fetchall()
            conn.close()

            query_vec = np.array(vector)
            results = []

            for text, vector_str, metadata_str in rows:
                if not vector_str:
                    continue
                v = np.array(json.loads(vector_str))
                dot = np.dot(query_vec, v)
                norm_q = np.linalg.norm(query_vec)
                norm_v = np.linalg.norm(v)

                if norm_q == 0 or norm_v == 0:
                    similarity = 0.0
                else:
                    similarity = dot / (norm_q * norm_v)

                results.append({
                    "text": text,
                    "metadata": json.loads(metadata_str) if metadata_str else {},
                    "score": float(similarity)
                })

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]
        except Exception:
            return []
