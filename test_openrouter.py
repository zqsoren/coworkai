#!/usr/bin/env python3
"""Test OpenRouter API with ChatOpenAI directly - run on server to diagnose 401"""
import asyncio

API_KEY = "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"
MODEL = "z-ai/glm-4.5-air:free"
BASE_URL = "https://openrouter.ai/api/v1"

print("=" * 60)
print("Test 1: Raw openai SDK (no langchain)")
print("=" * 60)
try:
    from openai import OpenAI
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "say hi"}],
        max_tokens=10
    )
    print(f"SUCCESS: {resp.choices[0].message.content}")
except Exception as e:
    print(f"FAILED: {e}")

print()
print("=" * 60)
print("Test 2: ChatOpenAI sync invoke")
print("=" * 60)
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    llm = ChatOpenAI(
        model=MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.7,
        max_tokens=10
    )
    resp = llm.invoke([HumanMessage(content="say hi")])
    print(f"SUCCESS: {resp.content}")
except Exception as e:
    print(f"FAILED: {e}")

print()
print("=" * 60)
print("Test 3: ChatOpenAI async ainvoke (this is what group chat uses)")
print("=" * 60)
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    llm = ChatOpenAI(
        model=MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.7,
        max_tokens=10
    )
    async def test_async():
        resp = await llm.ainvoke([HumanMessage(content="say hi")])
        print(f"SUCCESS: {resp.content}")
    asyncio.run(test_async())
except Exception as e:
    print(f"FAILED: {e}")

print()
print("=" * 60)
print("Test 4: With httpx custom headers")
print("=" * 60)
try:
    import httpx
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    headers = {"HTTP-Referer": "https://coworkai.xin", "X-Title": "BASE Coworker AI"}
    llm = ChatOpenAI(
        model=MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.7,
        max_tokens=10,
        http_client=httpx.Client(headers=headers),
        http_async_client=httpx.AsyncClient(headers=headers)
    )
    async def test_httpx():
        resp = await llm.ainvoke([HumanMessage(content="say hi")])
        print(f"SUCCESS: {resp.content}")
    asyncio.run(test_httpx())
except Exception as e:
    print(f"FAILED: {e}")

print()
print("=" * 60)
print("Test 5: Check versions")
print("=" * 60)
try:
    import openai; print(f"openai: {openai.__version__}")
except: print("openai: not installed")
try:
    import langchain_openai; print(f"langchain_openai: {langchain_openai.__version__}")
except: print("langchain_openai: not installed")
try:
    import httpx; print(f"httpx: {httpx.__version__}")
except: print("httpx: not installed")
