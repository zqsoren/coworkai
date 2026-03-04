"""
Util Router — 摘要/测试等辅助 API（Supabase 版）
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import datetime
import os
import traceback
from langchain_core.messages import HumanMessage

from backend.user_deps import get_user_llm_manager, get_user_group_manager, get_user_id

router = APIRouter(prefix="/api/util", tags=["utility"])


def log_debug(message: str):
    """Write debug logs to backend_debug.log"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [UtilRouter] {message}\n"
    print(log_line.strip())
    try:
        with open("backend_debug.log", "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print(f"Failed to write to log file: {e}")

class SummarizeRequest(BaseModel):
    fragments: List[str]
    workspace_id: Optional[str] = None
    group_id: Optional[str] = None
    agent_id: Optional[str] = None
    user_instruction: Optional[str] = None

@router.get("/test")
def test_connectivity():
    log_debug("Connectivity test requested")
    return {"status": "ok", "message": "Util router is reachable"}

@router.post("/summarize")
def summarize_text(req: SummarizeRequest, request: Request):
    """
    Summarize a list of text fragments using GLM 4.5 Air.
    """
    fragments = req.fragments
    log_debug(f"Received summarize request with {len(fragments)} fragments")
    
    if not fragments:
        log_debug("Empty fragments list, returning empty summary")
        return {"summary": ""}

    combined_text = "\n\n".join(fragments)

    # Build prompt
    user_instruction = (req.user_instruction or "").strip()

    if user_instruction:
        prompt = (
            "你是一个智能内容整理助手。请严格按照下方【最高指令】执行。\n\n"
            "## 最高指令（用户明确要求，必须遵守）\n"
            + user_instruction + "\n\n"
            "**其他规则：**\n"
            "1. 内容本身要完整保留（核心信息不得遗漏，不要凭空发挥）\n"
            "2. 可以删除纯粹是「组织标注」的词，如「标题4：」「选项A：」「素材：」等——这些是编辑备注，不是内容\n"
            "3. 可以打磨语句使其通顺，但不要大幅改写原意\n"
            "4. 表格直接用 | Markdown 格式，树状图用缩进列表，不要包裹在代码块里\n"
            "5. 直接输出整理后的内容，不要输出任何前言说明\n\n"
            "待整理的片段如下：\n"
            + combined_text
        )
    else:
        prompt = (
            "你是一个智能内容整理助手。请先判断用户给的这些片段想要做什么，然后根据意图输出对应格式的整理结果。\n\n"
            "## 第一步：意图判断（内部思考，不要输出）\n"
            "根据片段的特征判断场景，常见场景示例：\n"
            "- 若片段是若干独立选题/标题 → 用列表罗列\n"
            "- 若片段混有标题、正文、tag、不通顺的句子 → 整理为一篇完整帖子（标题 / 正文 / tag）\n"
            "- 若片段是几个案例或对比点 → 整理为对比表格\n"
            "- 若片段是几句相关联但零散的句子 → 融合成一段连贯的话\n"
            "- 若片段有其他明显结构 → 用最直观的方式呈现\n\n"
            "## 第二步：整理输出（只输出这部分）\n"
            "**规则：**\n"
            "1. 内容本身要完整保留（核心信息不得遗漏，不要凭空发挥）\n"
            "2. 可以删除纯粹是「组织标注」的词，如「标题4：」「选项A：」「素材：」等——这些是编辑备注，不是内容\n"
            "3. 可以打磨语句使其通顺，但不要大幅改写原意\n"
            "4. 表格直接用 | Markdown 格式，树状图用缩进列表，不要包裹在代码块里\n"
            "5. 直接输出整理后的表格、markdown、树状图、思维导图等，不要有仍和解释说明\n\n"
            "待整理的片段如下：\n"
            + combined_text
        )

    # Get user-scoped LLM manager
    llm_manager = get_user_llm_manager(request)

    fallback_models = [
        ("builtin_glm4air_free", "z-ai/glm-4.5-air:free"),
        ("builtin_qwen3coder_free", "qwen/qwen3-coder:free"),
        ("builtin_qwen3_free", "qwen/qwen3-4b:free"),
        ("builtin_gptoss_free", "openai/gpt-oss-120b:free")
    ]

    last_error = None
    for provider_id, model_name in fallback_models:
        try:
            log_debug(f"Initializing LLM model ({model_name})...")
            llm = llm_manager.get_model(provider_id, model_name)
            
            log_debug(f"Invoking LLM {model_name} (this may take up to 120s)...")
            response = llm.invoke([HumanMessage(content=prompt)])
            
            log_debug(f"LLM invocation successful with {model_name}!")
            
            if req.workspace_id and req.group_id:
                try:
                    group_manager = get_user_group_manager(request)
                    group_manager.add_message(
                        req.workspace_id,
                        req.group_id,
                        role="assistant",
                        content=response.content,
                        agent_name="System Summary"
                    )
                    log_debug(f"Saved summary to group {req.group_id}")
                except Exception as e:
                    log_debug(f"Failed to save summary to group history: {e}")

            return {"summary": response.content}
        except Exception as e:
            last_error = e
            log_debug(f"Model {model_name} failed: {str(e)}. Trying next...")
            continue
            
    error_msg = f"All free summarization models failed. Last error: {str(last_error)}"
    log_debug(f"CRITICAL ERROR: {error_msg}")
    raise HTTPException(status_code=500, detail=error_msg)
