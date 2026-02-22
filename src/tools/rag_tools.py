from langchain_core.tools import tool
from src.utils.rag_ingestion import RAGIngestion

def get_rag_tool(rag_system: RAGIngestion):
    """
    Factory to create a RAG search tool bound to a specific RAGIngestion instance.
    """
    
    @tool
    def search_knowledge_base(search_query: str) -> str:
        """
        在本地知识库或 ID 数据库中搜索相关的上下文信息。
        当用户询问特定的文档、内部知识，或者在你回答前需要核实事实时，请调用此工具。
        
        Args:
            search_query: 要搜索的具体问题或关键词。请尽量简明扼要，并针对搜索进行优化。
        """
        print(f"[RAG Tool] Searching for: {search_query}")
        try:
            docs = rag_system.query(search_query, top_k=3)
            if not docs:
                return "知识库中未找到相关信息。"
            
            result = "检索到的相关信息:\n\n"
            for d in docs:
                result += f"### 来源: {d['source']} (匹配度: {d['score']:.2f})\n{d['content'][:800]}\n\n"
            return result
        except Exception as e:
            return f"搜索过程中发生错误: {str(e)}"
            
    return search_knowledge_base
