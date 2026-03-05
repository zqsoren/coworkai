import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.supabase_client import supabase
import bcrypt

# 为 user_900c21dbbf9c 重置密码为 123456
new_password = "123456"
new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

print(f"New hash for '123456': {new_hash}")

result = supabase.table("users").update({
    "password_hash": new_hash
}).eq("id", "user_900c21dbbf9c").execute()

print(f"Updated: {result.data}")

# 验证
verify = supabase.table("users").select("password_hash").eq("id", "user_900c21dbbf9c").execute()
stored = verify.data[0]["password_hash"]
check = bcrypt.checkpw("123456".encode("utf-8"), stored.encode("utf-8"))
print(f"Verification: {check}")
