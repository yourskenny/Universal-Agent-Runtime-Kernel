import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import uuid
import os

class MemorySystem:
    def __init__(self, persist_path="./chroma_db"):
        print("正在初始化记忆系统 (ChromaDB + SentenceTransformer)...")
        # 1. 初始化向量数据库 (持久化存储)
        try:
            if hasattr(chromadb, 'PersistentClient'):
                self.client = chromadb.PersistentClient(path=persist_path)
            else:
                self.client = chromadb.Client(Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=persist_path
                ))
        except Exception as e:
            print(f"ChromaDB 初始化警告: {e}")
            self.client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=persist_path
            ))
        
        # 2. 初始化嵌入模型
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ 记忆系统准备就绪")

    def get_collection(self, name):
        """获取或创建指定名称的集合"""
        return self.client.get_or_create_collection(name=name)

    def add_memory(self, text, metadata=None, collection_name="long_term_memory"):
        """添加一条长期记忆到指定集合"""
        target_collection = self.get_collection(collection_name)
        embedding = self.embedding_model.encode(text).tolist()
        
        target_collection.add(
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata or {"source": "user_chat"}],
            ids=[str(uuid.uuid4())]
        )
        if hasattr(self.client, 'persist'):
            self.client.persist()
        return True

    def query_memory(self, query_text, n_results=3, collection_name="long_term_memory"):
        """从指定集合中检索相关记忆"""
        target_collection = self.get_collection(collection_name)
        
        count = target_collection.count()
        if count == 0:
            return []
        
        effective_n_results = min(n_results, count)
        query_embedding = self.embedding_model.encode(query_text).tolist()
        
        results = target_collection.query(
            query_embeddings=[query_embedding],
            n_results=effective_n_results
        )
        
        memories = []
        if results["documents"]:
            for doc in results["documents"][0]:
                memories.append(doc)
        return memories

    def count(self, collection_name="long_term_memory"):
        return self.get_collection(collection_name).count()
