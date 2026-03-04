"""
Supabase Client — 全局客户端初始化
提供统一的 Supabase 客户端实例供所有模块使用。
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# 加载 .env 文件
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError(
        "请在 .env 文件中配置 SUPABASE_URL 和 SUPABASE_SERVICE_KEY\n"
        "参考 .env 文件模板"
    )

# 使用 service_role key 创建客户端（后端专用，绕过 RLS）
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
