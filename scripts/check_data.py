import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.supabase_client import supabase

users = supabase.table("users").select("id,username,phone").execute()
print("=== USERS ===")
for u in users.data:
    print(f"  {u['id']} | {u['username']} | {u['phone']}")

print("\n=== AGENTS ===")
agents = supabase.table("agents").select("id,name,workspace,user_id").execute()
for a in agents.data:
    print(f"  [{a['user_id']}] {a['id']} -> {a['name']} (ws: {a['workspace']})")

print("\n=== WORKSPACES ===")
ws = supabase.table("workspaces").select("id,name,user_id").execute()
for w in ws.data:
    print(f"  [{w['user_id']}] {w['id']} -> {w['name']}")
