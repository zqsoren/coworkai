"""
将服务器旧用户 user_844afbfdda04 的所有数据合并到 user_900c21dbbf9c

此脚本会：
1. 检查两个用户各自有多少数据
2. 将 user_844afbfdda04 的 agents/workspaces/llm_providers/scheduled_tasks/group_chats 
   的 user_id 全部改成 user_900c21dbbf9c
3. 删除重复的 user_844afbfdda04 用户记录
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.supabase_client import supabase

OLD_USER = "user_844afbfdda04"
NEW_USER = "user_900c21dbbf9c"

TABLES_WITH_USER_ID = [
    "agents",
    "workspaces", 
    "llm_providers",
    "scheduled_tasks",
    "group_chats",
    "inbox",
    "output_modes",
]

def main():
    print(f"=== 合并用户数据: {OLD_USER} -> {NEW_USER} ===\n")
    
    # Step 1: 检查数据
    print("--- 当前数据分布 ---")
    for table in TABLES_WITH_USER_ID:
        try:
            old = supabase.table(table).select("id").eq("user_id", OLD_USER).execute()
            new = supabase.table(table).select("id").eq("user_id", NEW_USER).execute()
            print(f"  {table:20s}: 旧用户={len(old.data)}条, 新用户={len(new.data)}条")
        except Exception as e:
            print(f"  {table:20s}: 查询失败 ({e})")
    
    # Check users table
    users = supabase.table("users").select("*").execute()
    print(f"\n--- 用户表 ---")
    for u in users.data:
        print(f"  {u['id']} | {u.get('username','')} | {u.get('phone','')}")
    
    # Step 2: 迁移数据
    print(f"\n--- 开始迁移 ---")
    total_migrated = 0
    for table in TABLES_WITH_USER_ID:
        try:
            old_data = supabase.table(table).select("id").eq("user_id", OLD_USER).execute()
            if old_data.data:
                ids = [row["id"] for row in old_data.data]
                for row_id in ids:
                    supabase.table(table).update({"user_id": NEW_USER}).eq("id", row_id).execute()
                print(f"  ✅ {table}: 迁移了 {len(ids)} 条记录")
                total_migrated += len(ids)
            else:
                print(f"  ⏭️  {table}: 无需迁移 (0条)")
        except Exception as e:
            print(f"  ❌ {table}: 迁移失败 ({e})")
    
    # Step 3: 删除旧用户（如果存在）
    try:
        old_user = supabase.table("users").select("id").eq("id", OLD_USER).execute()
        if old_user.data:
            supabase.table("users").delete().eq("id", OLD_USER).execute()
            print(f"\n  🗑️  已删除旧用户记录: {OLD_USER}")
    except Exception as e:
        print(f"\n  ⚠️  删除旧用户失败: {e}")
    
    # Step 4: 验证
    print(f"\n--- 迁移完成，验证结果 ---")
    for table in TABLES_WITH_USER_ID:
        try:
            remaining = supabase.table(table).select("id").eq("user_id", OLD_USER).execute()
            current = supabase.table(table).select("id").eq("user_id", NEW_USER).execute()
            status = "✅" if len(remaining.data) == 0 else "⚠️"
            print(f"  {status} {table:20s}: 旧={len(remaining.data)}, 新={len(current.data)}")
        except Exception as e:
            print(f"  ❌ {table}: {e}")
    
    print(f"\n总共迁移了 {total_migrated} 条记录")

if __name__ == "__main__":
    main()
