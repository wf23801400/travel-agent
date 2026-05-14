"""LLM 调用封装 — 支持 DeepSeek 和 Claude API，Pydantic 结构化输出。"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Callable, Optional

import httpx
from pydantic import BaseModel

from src.models.settings import Settings

logger = logging.getLogger(__name__)

DEEPSEEK_BASE = "https://api.deepseek.com"
CLAUDE_BASE = "https://api.anthropic.com"

_client: Optional["LLMClient"] = None


def get_llm_client() -> "LLMClient":
    """获取 LLMClient 单例。"""
    global _client
    if _client is None:
        _client = LLMClient(Settings())
    return _client


def reset_llm_client() -> None:
    """重置 LLM 客户端单例（主要用于测试）。"""
    global _client
    _client = None


class LLMClient:
    """统一 LLM 调用客户端，支持 DeepSeek（默认）和 Claude。"""

    def __init__(self, settings: Settings) -> None:
        self._provider = settings.llm_provider
        self._deepseek_key = settings.deepseek_api_key
        self._deepseek_base = settings.deepseek_api_base
        self._claude_key = settings.claude_api_key
        self._timeout = 30.0
        self._max_retries = 2
        self._model = "deepseek-chat" if self._provider == "deepseek" else "claude-sonnet-4-6"

    @property
    def is_available(self) -> bool:
        if self._provider == "deepseek":
            return bool(self._deepseek_key)
        return bool(self._claude_key)

    @property
    def provider(self) -> str:
        return self._provider

    async def chat(
        self,
        messages: list[dict],
        response_model: Optional[type[BaseModel]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream_callback: Optional[Callable[[str], Any]] = None,
    ) -> str | BaseModel:
        """发送对话请求，可选结构化输出。

        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            response_model: 可选 Pydantic 模型，用于约束结构化输出
            temperature: 采样温度
            max_tokens: 最大生成 token 数
            stream_callback: 流式回调，每收到一个增量文本调用一次

        Returns:
            str: 无 response_model 时返回纯文本
            BaseModel: 有 response_model 时返回解析后的 Pydantic 实例
        """
        if not self.is_available:
            return _fallback_text(response_model, "LLM API key 未配置")

        if self._provider == "deepseek":
            return await self._chat_deepseek(messages, response_model, temperature, max_tokens, stream_callback)
        return await self._chat_claude(messages, response_model, temperature, max_tokens, stream_callback)

    async def _chat_deepseek(
        self,
        messages: list[dict],
        response_model: Optional[type[BaseModel]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream_callback: Optional[Callable[[str], Any]] = None,
    ) -> str | BaseModel:
        """调用 DeepSeek API。"""
        url = f"{self._deepseek_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._deepseek_key}",
            "Content-Type": "application/json",
        }

        body: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_model is not None:
            schema = _pydantic_to_json_schema(response_model)
            body["tools"] = [{
                "type": "function",
                "function": {
                    "name": "respond",
                    "description": f"返回结构化的 {response_model.__name__} 数据",
                    "parameters": schema,
                },
            }]
            body["tool_choice"] = {"type": "function", "function": {"name": "respond"}}

        if stream_callback is not None:
            body["stream"] = True

        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    if stream_callback is not None:
                        collected = ""
                        async with client.stream("POST", url, json=body, headers=headers) as resp:
                            resp.raise_for_status()
                            async for line in resp.aiter_lines():
                                if line.startswith("data: "):
                                    data = line[6:]
                                    if data == "[DONE]":
                                        break
                                    try:
                                        chunk = json.loads(data)
                                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            collected += content
                                            stream_callback(content)
                                    except json.JSONDecodeError:
                                        continue
                        full_text = collected
                    else:
                        resp = await client.post(url, json=body, headers=headers)
                        resp.raise_for_status()
                        result = resp.json()

                    if response_model is None:
                        if stream_callback is None:
                            full_text = result["choices"][0]["message"]["content"]
                        return full_text

                    if stream_callback is None:
                        tool_calls = result["choices"][0]["message"].get("tool_calls", [])
                        if tool_calls:
                            args_str = tool_calls[0]["function"]["arguments"]
                            parsed = json.loads(args_str)
                            return response_model.model_validate(parsed)
                        raw = result["choices"][0]["message"]["content"]
                        return response_model.model_validate_json(raw)
                    return collected

            except httpx.TimeoutException:
                logger.warning("DeepSeek API 超时 (第%d次)", attempt + 1)
            except httpx.HTTPStatusError as e:
                logger.warning("DeepSeek API HTTP %d (第%d次)", e.response.status_code, attempt + 1)
            except Exception as e:
                logger.warning("DeepSeek API 异常: %s (第%d次)", str(e), attempt + 1)

            if attempt < self._max_retries - 1:
                await asyncio.sleep(2**attempt)

        return _fallback_text(response_model, "DeepSeek API 调用失败")

    async def _chat_claude(
        self,
        messages: list[dict],
        response_model: Optional[type[BaseModel]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream_callback: Optional[Callable[[str], Any]] = None,
    ) -> str | BaseModel:
        """调用 Claude (Anthropic) API。"""
        url = f"{CLAUDE_BASE}/v1/messages"
        headers = {
            "x-api-key": self._claude_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        system_msg = ""
        user_msgs: list[dict] = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                user_msgs.append(m)

        body: dict[str, Any] = {
            "model": self._model,
            "messages": user_msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_msg:
            body["system"] = system_msg

        if response_model is not None:
            schema = _pydantic_to_json_schema(response_model)
            body["tools"] = [{
                "name": "respond",
                "description": f"返回结构化的 {response_model.__name__} 数据",
                "input_schema": schema,
            }]
            body["tool_choice"] = {"type": "tool", "name": "respond"}

        if stream_callback is not None:
            body["stream"] = True

        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    if stream_callback is not None:
                        collected = ""
                        async with client.stream("POST", url, json=body, headers=headers) as resp:
                            resp.raise_for_status()
                            async for line in resp.aiter_lines():
                                if line.startswith("data: "):
                                    data = line[6:]
                                    try:
                                        event = json.loads(data)
                                        if event.get("type") == "content_block_delta":
                                            delta = event.get("delta", {})
                                            text = delta.get("text", "")
                                            if text:
                                                collected += text
                                                stream_callback(text)
                                    except json.JSONDecodeError:
                                        continue
                        full_text = collected
                    else:
                        resp = await client.post(url, json=body, headers=headers)
                        resp.raise_for_status()
                        result = resp.json()

                    if response_model is None:
                        if stream_callback is None:
                            for block in result.get("content", []):
                                if block.get("type") == "text":
                                    full_text = block.get("text", "")
                                    break
                        return full_text

                    if stream_callback is None:
                        for block in result.get("content", []):
                            if block.get("type") == "tool_use":
                                args = block.get("input", {})
                                return response_model.model_validate(args)
                        for block in result.get("content", []):
                            if block.get("type") == "text":
                                return response_model.model_validate_json(block.get("text", "{}"))
                        return _fallback_text(response_model, "Claude 返回无工具调用")

                    return collected

            except httpx.TimeoutException:
                logger.warning("Claude API 超时 (第%d次)", attempt + 1)
            except httpx.HTTPStatusError as e:
                logger.warning("Claude API HTTP %d (第%d次)", e.response.status_code, attempt + 1)
            except Exception as e:
                logger.warning("Claude API 异常: %s (第%d次)", str(e), attempt + 1)

            if attempt < self._max_retries - 1:
                await asyncio.sleep(2**attempt)

        return _fallback_text(response_model, "Claude API 调用失败")

    async def stream_chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """流式对话，逐 token 产出文本。

        Args:
            messages: 消息列表
            temperature: 采样温度
            max_tokens: 最大 token 数

        Yields:
            str: 每个增量文本片段
        """
        queue: asyncio.Queue = asyncio.Queue()

        async def _cb(text: str) -> None:
            await queue.put(text)

        async def _runner() -> None:
            await self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream_callback=_cb,
            )
            await queue.put(None)  # sentinel

        task = asyncio.create_task(_runner())
        while True:
            text = await queue.get()
            if text is None:
                break
            yield text
        await task


def _pydantic_to_json_schema(model: type[BaseModel]) -> dict:
    """将 Pydantic v2 模型转为 JSON Schema dict。"""
    schema = model.model_json_schema()
    _clean_schema(schema)
    return schema


def _clean_schema(schema: dict) -> None:
    """移除 Pydantic JSON Schema 中 LLM API 不支持的字段。"""
    schema.pop("title", None)
    if "properties" in schema:
        for prop in schema["properties"].values():
            if isinstance(prop, dict):
                prop.pop("title", None)
                if "properties" in prop:
                    _clean_schema(prop)
                if "items" in prop and isinstance(prop["items"], dict):
                    prop["items"].pop("title", None)


def _fallback_text(response_model: Optional[type[BaseModel]], reason: str) -> str | BaseModel:
    """生成兜底返回值。"""
    if response_model is None:
        return f"[错误] {reason}"
    try:
        return response_model()
    except Exception:
        return f"[错误] {reason}"
