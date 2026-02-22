"""
Deep Research Skill（Layer 2 标准技能）
链式调用：Search -> Scrape Top 5 -> Summarize -> Generate Markdown Report
"""

SKILL_NAME = "deep_research"
SKILL_DESCRIPTION = "深度研究：搜索 → 抓取前5条 → 摘要 → 生成 Markdown 报告"


async def run(query: str, llm=None, search_tool=None, fetch_tool=None, **kwargs) -> str:
    """
    执行深度研究流程
    
    Args:
        query: 研究主题
        llm: LLM 实例（用于摘要生成）
        search_tool: 搜索工具函数
        fetch_tool: 网页抓取工具函数
    """
    results = []
    
    # Step 1: 搜索
    if search_tool:
        search_results = search_tool.invoke(query)
    else:
        search_results = f"（搜索功能未配置，跳过搜索步骤）\n查询: {query}"
    
    # Step 2: 抓取前 5 条结果
    # 从搜索结果中提取 URL（简单解析）
    urls = []
    for line in search_results.split("\n"):
        if "链接:" in line:
            url = line.split("链接:")[1].strip()
            urls.append(url)
    
    contents = []
    for url in urls[:5]:
        if fetch_tool:
            content = fetch_tool.invoke(url)
            contents.append({"url": url, "content": content[:2000]})
    
    # Step 3: 生成报告
    if llm:
        prompt = f"""请基于以下搜索结果和网页内容，生成一份关于 "{query}" 的详细 Markdown 研究报告。
要求：
1. 包含摘要、关键发现、详细分析和结论
2. 引用信息来源
3. 使用中文撰写

搜索结果:
{search_results}

抓取的网页内容:
"""
        for c in contents:
            prompt += f"\n---\n来源: {c['url']}\n{c['content']}\n"
        
        response = llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
    else:
        # 无 LLM 时返回原始数据
        report = f"# 研究报告: {query}\n\n## 搜索结果\n{search_results}\n"
        for c in contents:
            report += f"\n## 来源: {c['url']}\n{c['content'][:500]}\n"
        return report
