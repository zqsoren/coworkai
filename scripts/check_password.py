import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.supabase_client import supabase
import bcrypt

# 查看用户密码 hash
users = supabase.table("users").select("id,username,phone,password_hash").eq("phone", "19838925905").execute()
for u in users.data:
    print(f"User: {u['id']} | {u['username']} | {u['phone']}")
    h = u['password_hash']
    print(f"Hash: {h}")
    print(f"Hash length: {len(h)}")
    
    # 测试密码验证
    try:
        result = bcrypt.checkpw("123456".encode("utf-8"), h.encode("utf-8"))
        print(f"Password '123456' matches: {result}")
    except Exception as e:
        print(f"Password check error: {e}")
    print()
