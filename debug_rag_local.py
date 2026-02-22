
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from src.utils.rag_ingestion import RAGIngestion, TextSplitterService

DATA_ROOT = "data"
WORKSPACE = "workspace_啊啊"
AGENT_ID = "agent_fan"

def main():
    print(f"Checking data root: {os.path.abspath(DATA_ROOT)}")
    kb_path = os.path.join(DATA_ROOT, WORKSPACE, AGENT_ID, "knowledge_base")
    print(f"Target KB path: {kb_path}")
    
    if not os.path.exists(kb_path):
        print("KB Path does not exist!")
        return
        
    files = os.listdir(kb_path)
    print(f"Files found: {files}")
    
    ingestion = RAGIngestion(DATA_ROOT, WORKSPACE, AGENT_ID)
    
    for f in files:
        fpath = os.path.join(kb_path, f)
        print(f"\nProcessing: {f}")
        try:
            # 1. Load
            text = ingestion._load(fpath)
            print(f"  - Loaded length: {len(text)}")
            if not text:
                print("  - Text is empty!")
                continue
                
            # 2. Clean
            cleaned = ingestion._clean(text)
            print(f"  - Cleaned length: {len(cleaned)}")
            
            # 3. Split
            splitter = TextSplitterService()
            chunks = splitter.split_text(cleaned, chunk_size=500, chunk_overlap=50)
            print(f"  - Chunks generated: {len(chunks)}")
            if chunks:
                print(f"  - Sample chunk: {chunks[0][:50]}...")
            
            # 4. Integrate Call
            # We don't want to mess up the vector store if it's working, but let's see what ingest_file returns
            count = ingestion.ingest_file(fpath)
            print(f"  - ingest_file returned: {count}")
            
        except Exception as e:
            print(f"  - Error: {e}")

if __name__ == "__main__":
    main()
