"""
WebTools - 网络工具（Layer 1 核心工具）
提供搜索和网页内容抓取能力。
"""

from langchain_core.tools import tool


@tool
def google_search(query: str) -> str:
    """使用搜索引擎搜索信息，返回前 10 条结果的标题和链接。
    
    Args:
        query: 搜索查询词
    """
    try:
        from tavily import TavilyClient
        import streamlit as st
        
        api_key = st.secrets.get("search", {}).get("tavily_api_key", "")
        if not api_key:
            return "搜索 API Key 未配置。请在设置中填入 Tavily API Key。"
        
        client = TavilyClient(api_key=api_key)
        results = client.search(query, max_results=10)
        
        lines = [f"搜索结果: {query}\n"]
        for i, r in enumerate(results.get("results", []), 1):
            lines.append(f"{i}. **{r['title']}**")
            lines.append(f"   链接: {r['url']}")
            lines.append(f"   摘要: {r.get('content', '无')[:200]}")
            lines.append("")
        return "\n".join(lines)
    except ImportError:
        return "Tavily 库未安装。请运行: pip install tavily-python"
    except Exception as e:
        return f"搜索出错: {str(e)}"


@tool
def fetch_url_content(url: str) -> str:
    """以阅读模式抓取网页正文内容，去除广告和导航元素。
    
    Args:
        url: 要抓取的网页 URL
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 移除脚本、样式、导航等元素
        for tag in soup(["script", "style", "nav", "header", "footer",
                         "aside", "iframe", "noscript"]):
            tag.decompose()
        
        # 提取正文
        text = soup.get_text(separator="\n", strip=True)
        
        # 清理多余空行
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        content = "\n".join(lines)
        
        # 限制长度
        if len(content) > 8000:
            content = content[:8000] + "\n\n...[内容已截断]"
        
        return f"网页内容 ({url}):\n\n{content}"
    except requests.RequestException as e:
        return f"网页抓取失败: {str(e)}"
    except Exception as e:
        return f"解析出错: {str(e)}"


WEB_TOOLS = [google_search, fetch_url_content]
