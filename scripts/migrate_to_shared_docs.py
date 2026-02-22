"""
数据迁移脚本 - 将现有 Agent 私有文档迁移到工作区共享目录

将:
  data/{workspace}/{agent}/context/static/*  -> data/{workspace}/shared/static/
  data/{workspace}/{agent}/context/active/*  -> data/{workspace}/shared/active/
  
保留:
  data/{workspace}/{agent}/archives/  (不迁移，保持私有)
  data/{workspace}/{agent}/knowledge_base/
  data/{workspace}/{agent}/vector_store/
"""

import os
import shutil
import json
from pathlib import Path


def migrate_workspace(data_root: str, workspace_id: str, dry_run: bool = True):
    """
    迁移单个工作区的旧文档到 shared 目录
    
    Args:
        data_root: data/ 目录路径
        workspace_id: 工作区 ID (e.g., "workspace_default")
        dry_run: 如果为 True，只打印操作不实际执行
    """
    workspace_path = os.path.join(data_root, workspace_id)
    
    if not os.path.exists(workspace_path):
        print(f"⚠️  工作区不存在: {workspace_id}")
        return
    
    # 1. 创建 shared 目录
    shared_static = os.path.join(workspace_path, "shared", "static")
    shared_active = os.path.join(workspace_path, "shared", "active")
    
    if dry_run:
        print(f"[DRY-RUN] 将创建目录: {shared_static}")
        print(f"[DRY-RUN] 将创建目录: {shared_active}")
    else:
        os.makedirs(shared_static, exist_ok=True)
        os.makedirs(shared_active, exist_ok=True)
        print(f"✅ 创建共享目录: shared/static/ 和 shared/active/")
    
    # 2. 遍历所有 Agent
    migrated_count = 0
    for item in os.listdir(workspace_path):
        agent_path = os.path.join(workspace_path, item)
        
        # 跳过非目录和特殊目录
        if not os.path.isdir(agent_path) or item in ["shared", ".git"]:
            continue
        
        # 跳过元数据文件目录
        if item.startswith("_") or item.startswith("."):
            continue
        
        agent_id = item
        print(f"\n📁 处理 Agent: {agent_id}")
        
        # 3. 迁移 static/ 文档
        old_static = os.path.join(agent_path, "context", "static")
        if os.path.exists(old_static) and os.listdir(old_static):
            for filename in os.listdir(old_static):
                src = os.path.join(old_static, filename)
                # 添加 agent_id 前缀避免冲突
                dst_filename = f"{agent_id}_{filename}"
                dst = os.path.join(shared_static, dst_filename)
                
                if os.path.isfile(src):
                    if dry_run:
                        print(f"  [DRY-RUN] Move: {src} -> {dst}")
                    else:
                        shutil.move(src, dst)
                        print(f"  ✅ Moved: {filename} -> shared/static/{dst_filename}")
                    migrated_count += 1
        
        # 4. 迁移 active/ 文档
        old_active = os.path.join(agent_path, "context", "active")
        if os.path.exists(old_active) and os.listdir(old_active):
            for filename in os.listdir(old_active):
                src = os.path.join(old_active, filename)
                # 添加 agent_id 前缀避免冲突
                dst_filename = f"{agent_id}_{filename}"
                dst = os.path.join(shared_active, dst_filename)
                
                if os.path.isfile(src):
                    if dry_run:
                        print(f"  [DRY-RUN] Move: {src} -> {dst}")
                    else:
                        shutil.move(src, dst)
                        print(f"  ✅ Moved: {filename} -> shared/active/{dst_filename}")
                    migrated_count += 1
        
        # 5. 清理空的旧目录
        old_context = os.path.join(agent_path, "context")
        if os.path.exists(old_context):
            # 删除 static/ 和 active/ 空目录
            for subdir in ["static", "active"]:
                subdir_path = os.path.join(old_context, subdir)
                if os.path.exists(subdir_path) and not os.listdir(subdir_path):
                    if dry_run:
                        print(f"  [DRY-RUN] 删除空目录: {subdir_path}")
                    else:
                        os.rmdir(subdir_path)
                        print(f"  🗑️  删除空目录: context/{subdir}/")
    
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}✅ 迁移完成！共处理 {migrated_count} 个文件")


def migrate_all_workspaces(data_root: str, dry_run: bool = True):
    """
    迁移所有工作区
    
    Args:
        data_root: data/ 目录路径
        dry_run: 如果为 True，只打印操作不实际执行
    """
    if not os.path.exists(data_root):
        print(f"❌ 数据根目录不存在: {data_root}")
        return
    
    print(f"{'='*60}")
    print(f"文档共享架构迁移脚本")
    print(f"{'='*60}")
    print(f"数据目录: {data_root}")
    print(f"模式: {'DRY-RUN (预览)' if dry_run else 'LIVE (实际执行)'}")
    print(f"{'='*60}\n")
    
    # 扫描所有工作区
    workspaces = []
    for item in os.listdir(data_root):
        item_path = os.path.join(data_root, item)
        if os.path.isdir(item_path) and item.startswith("workspace_"):
            workspaces.append(item)
    
    if not workspaces:
        print("⚠️  未找到任何工作区")
        return
    
    print(f"发现 {len(workspaces)} 个工作区: {', '.join(workspaces)}\n")
    
    for workspace_id in workspaces:
        migrate_workspace(data_root, workspace_id, dry_run)
        print(f"\n{'-'*60}\n")


if __name__ == "__main__":
    import sys
    
    # 脚本路径: scripts/migrate_to_shared_docs.py
    # 从项目根目录运行
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_root = os.path.join(project_root, "data")
    
    # 检查命令行参数
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        dry_run = False
        print("\n⚠️  警告：即将实际执行迁移！")
        response = input("确认继续？(yes/no): ")
        if response.lower() != "yes":
            print("❌ 已取消")
            sys.exit(0)
    
    # 执行迁移
    migrate_all_workspaces(data_root, dry_run)
    
    if dry_run:
        print("\n💡 这是预览模式。要实际执行迁移，请运行:")
        print(f"   python scripts/migrate_to_shared_docs.py --execute")
