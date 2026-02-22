
import os
import chromadb
import sys

def inspect_chromadb(workspace="workspace_default"):
    # Path construction
    project_root = os.getcwd()
    data_root = os.path.join(project_root, "data")
    workspace_path = os.path.join(data_root, workspace)
    
    output_file = "debug_rag_output.txt"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"Scanning Workspace: {workspace}\n\n")
        
        if not os.path.exists(workspace_path):
             f.write(f"Workspace path {workspace_path} does not exist.\n")
             return

        agents = [d for d in os.listdir(workspace_path) if os.path.isdir(os.path.join(workspace_path, d))]
        
        found_data = False
        
        for agent_id in agents:
            if agent_id.startswith("_") or agent_id in ["shared", "static_assets", "living_docs"]:
                continue
                
            vs_path = os.path.join(workspace_path, agent_id, "vector_store")
            if not os.path.exists(vs_path):
                continue
                
            try:
                # Check if dir is empty
                if not os.listdir(vs_path):
                    continue

                client = chromadb.PersistentClient(path=vs_path)
                collections = client.list_collections()
                
                if not collections:
                    continue
                    
                for col in collections:
                    count = col.count()
                    if count > 0:
                        f.write(f"✅ Found Data in Agent: {agent_id}\n")
                        f.write(f"   Collection: {col.name}\n")
                        f.write(f"   Total Documents: {count}\n\n")
                        
                        results = col.peek(limit=5)
                        
                        f.write("=== Top 5 Documents ===\n\n")
                        ids = results['ids']
                        metadatas = results['metadatas']
                        documents = results['documents']
                        
                        for i in range(len(ids)):
                            f.write(f"[{i+1}] ID: {ids[i]}\n")
                            f.write(f"    Metadata: {metadatas[i]}\n")
                            f.write(f"    Content: {documents[i][:150].replace(chr(10), ' ')}...\n")
                            f.write("-" * 50 + "\n")
                        
                        found_data = True
                        break
                
                if found_data:
                    break
                    
            except Exception as e:
                f.write(f"Error inspecting {agent_id}: {e}\n")
        
        if not found_data:
            f.write("❌ No data found in any agent's vector store.\n")

    print(f"Done. Output written to {output_file}")

if __name__ == "__main__":
    inspect_chromadb()
