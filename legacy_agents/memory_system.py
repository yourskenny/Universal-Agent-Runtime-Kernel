import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import uuid
import os

class MemorySystem:
    def __init__(self, persist_path="./chroma_db"):
        print("正在初始化记忆系统 (ChromaDB + SentenceTransformer)...")
        # 1. 初始化向量数据库 (持久化存储)
        # 适配 ChromaDB 0.3.x 版本: 使用 Client 并配合 Settings 设置持久化
        try:
            # 尝试新版 API (以防未来升级)
            if hasattr(chromadb, 'PersistentClient'):
                self.client = chromadb.PersistentClient(path=persist_path)
            else:
                # 旧版 API (0.3.x)
                self.client = chromadb.Client(Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=persist_path
                ))
        except Exception as e:
            print(f"ChromaDB 初始化警告: {e}")
            # 降级尝试
            self.client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=persist_path
            ))
        
        # 2. 初始化嵌入模型 (用于将文本转为向量)
        # 使用轻量级模型 all-MiniLM-L6-v2，无需联网下载大模型
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 3. 获取或创建集合
        # 默认 "long_term_memory"
        self.collection = self.client.get_or_create_collection(name="long_term_memory")
        print("✅ 记忆系统准备就绪")

    def get_collection(self, name):
        """获取或创建指定名称的集合 (用于多智能体专精)"""
        return self.client.get_or_create_collection(name=name)

    def add_memory(self, text, metadata=None, collection_name="long_term_memory"):
        """添加一条长期记忆到指定集合"""
        # 切换到目标集合
        target_collection = self.get_collection(collection_name)
        
        # 生成向量
        embedding = self.embedding_model.encode(text).tolist()
        
        # 存入数据库
        target_collection.add(
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata or {"source": "user_chat"}],
            ids=[str(uuid.uuid4())]
        )
        # 旧版 ChromaDB 需要手动 persist
        if hasattr(self.client, 'persist'):
            self.client.persist()
        return True

    def query_memory(self, query_text, n_results=3, collection_name="long_term_memory"):
        """从指定集合中检索相关记忆"""
        target_collection = self.get_collection(collection_name)
        
        # --- 修复：动态调整 n_results ---
        # 如果数据库里的条目少于 n_results，就只检索当前拥有的条目数
        count = target_collection.count()
        if count == 0:
            return []
        
        effective_n_results = min(n_results, count)
        
        query_embedding = self.embedding_model.encode(query_text).tolist()
        
        results = target_collection.query(
            query_embeddings=[query_embedding],
            n_results=effective_n_results
        )
        
        # 整理结果
        memories = []
        if results["documents"]:
            for doc in results["documents"][0]:
                memories.append(doc)
        return memories

    def count(self, collection_name="long_term_memory"):
        return self.get_collection(collection_name).count()

if __name__ == "__main__":
    # 简单测试
    mem = MemorySystem()
    mem.add_memory("我叫张三，是一名Python工程师。")
    mem.add_memory("我喜欢吃火锅，特别是麻辣锅。")
    mem.add_memory("明天的会议在上午10点。")
    
    print(f"当前记忆数量: {mem.count()}")
    
    query = "我喜欢吃什么？"
    print(f"查询: {query}")
    results = mem.query_memory(query)
    print("检索结果:", results)
