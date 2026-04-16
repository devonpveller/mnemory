"""
title: Mnemory Tools
description: Memory tools for storing, searching, and managing persistent memories. The filter handles automatic recall — use these tools for explicit operations.
author: mnemory
version: 0.1.0
license: Apache-2.0
"""

import json
import logging
from typing import Any, Callable, Optional

import aiohttp
from pydantic import BaseModel, Field

_log = logging.getLogger(__name__)


class Tools:
    class Valves(BaseModel):
        mnemory_url: str = Field(
            default="http://localhost:8050",
            description="Mnemory server base URL",
        )
        api_key: str = Field(
            default="",
            description="API key for mnemory authentication",
        )
        agent_id: str = Field(
            default="open-webui",
            description="Agent ID sent to mnemory",
        )
        request_timeout: int = Field(
            default=30,
            description="HTTP request timeout in seconds",
        )

    def __init__(self):
        self.valves = self.Valves()

    def _headers(self, user: dict) -> dict:
        """Build request headers with auth and identity."""
        headers = {
            "Content-Type": "application/json",
            "X-Agent-Id": self.valves.agent_id,
            "X-User-Id": user.get("email", user.get("id", "")),
        }
        if self.valves.api_key:
            headers["Authorization"] = f"Bearer {self.valves.api_key}"
        return headers

    async def _post(
        self,
        path: str,
        payload: dict,
        user: dict,
    ) -> dict:
        """POST to mnemory REST API. Returns parsed JSON or error dict."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.valves.mnemory_url}{path}",
                    headers=self._headers(user),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.valves.request_timeout),
                ) as resp:
                    body = await resp.json()
                    if resp.status == 200:
                        return body
                    detail = body.get("detail", resp.reason)
                    return {"error": True, "status": resp.status, "detail": str(detail)}
        except Exception as exc:
            _log.exception("mnemory API error: %s %s", path, exc)
            return {"error": True, "message": f"Connection error: {exc}"}

    async def _put(
        self,
        path: str,
        payload: dict,
        user: dict,
    ) -> dict:
        """PUT to mnemory REST API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{self.valves.mnemory_url}{path}",
                    headers=self._headers(user),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.valves.request_timeout),
                ) as resp:
                    body = await resp.json()
                    if resp.status == 200:
                        return body
                    detail = body.get("detail", resp.reason)
                    return {"error": True, "status": resp.status, "detail": str(detail)}
        except Exception as exc:
            _log.exception("mnemory API error: %s %s", path, exc)
            return {"error": True, "message": f"Connection error: {exc}"}

    async def _delete(
        self,
        path: str,
        user: dict,
    ) -> dict:
        """DELETE to mnemory REST API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.valves.mnemory_url}{path}",
                    headers=self._headers(user),
                    timeout=aiohttp.ClientTimeout(total=self.valves.request_timeout),
                ) as resp:
                    body = await resp.json()
                    if resp.status == 200:
                        return body
                    detail = body.get("detail", resp.reason)
                    return {"error": True, "status": resp.status, "detail": str(detail)}
        except Exception as exc:
            _log.exception("mnemory API error: %s %s", path, exc)
            return {"error": True, "message": f"Connection error: {exc}"}

    # ── Tool: remember ────────────────────────────────────────────────

    async def remember(
        self,
        content: str,
        __user__: dict = {},
        __event_emitter__: Optional[Callable] = None,
    ) -> str:
        """Store a memory. Just pass the content — the server handles classification automatically.

        Call this when the user shares something worth remembering: personal info,
        preferences, decisions, tasks, project context, or corrections.

        Do NOT pass categories, memory_type, or importance — the server auto-classifies.

        Args:
            content: The fact, preference, decision, or detail to remember (max 1000 chars).

        Returns:
            Confirmation with memory ID, or an error message.
        """
        if not content or not content.strip():
            return json.dumps({"error": True, "message": "Content cannot be empty"})

        if len(content) > 1000:
            return json.dumps(
                {"error": True, "message": f"Content too long ({len(content)} chars, max 1000). Summarize first."}
            )

        if __event_emitter__:
            await __event_emitter__(
                {"type": "status", "data": {"description": "Storing memory...", "done": False}}
            )

        result = await self._post("/api/memories", {"content": content}, __user__)

        if __event_emitter__:
            if result.get("error"):
                desc = f"Memory error: {result.get('detail') or result.get('message', 'unknown')}"
            else:
                count = len(result.get("results", []))
                desc = f"Stored {count} memory item(s)" if count else "Memory processed (deduplicated)"
            await __event_emitter__(
                {"type": "status", "data": {"description": desc, "done": True}}
            )

        return json.dumps(result, default=str)

    # ── Tool: search_memory ───────────────────────────────────────────

    async def search_memory(
        self,
        query: str,
        __user__: dict = {},
        __event_emitter__: Optional[Callable] = None,
    ) -> str:
        """Search memories using natural language. Use this to look up anything about the user.

        You do NOT need exact names — describe what you're looking for naturally.
        Examples: "what pets does the user have", "Tennessee utilities task",
        "preferences for code style", "recent decisions about the project".

        Args:
            query: What to search for, in natural language.

        Returns:
            List of matching memories with content, type, and metadata.
        """
        if not query or not query.strip():
            return json.dumps({"error": True, "message": "Query cannot be empty"})

        if __event_emitter__:
            await __event_emitter__(
                {"type": "status", "data": {"description": "Searching memories...", "done": False}}
            )

        result = await self._post(
            "/api/memories/search",
            {"query": query, "limit": 10},
            __user__,
        )

        if __event_emitter__:
            if result.get("error"):
                desc = f"Search error: {result.get('detail') or result.get('message', 'unknown')}"
            else:
                count = len(result.get("results", []))
                desc = f"Found {count} memories" if count else "No matching memories found"
            await __event_emitter__(
                {"type": "status", "data": {"description": desc, "done": True}}
            )

        return json.dumps(result, default=str)

    # ── Tool: find_memory ─────────────────────────────────────────────

    async def find_memory(
        self,
        question: str,
        __user__: dict = {},
        __event_emitter__: Optional[Callable] = None,
    ) -> str:
        """Deep search for memories using AI-powered multi-query expansion and reranking.

        Use this for complex questions that need thorough searching across
        related topics. Slower than search_memory (2 extra LLM calls) but
        finds more relevant results by following associations.

        Examples: "What do I know about the user's move to Tennessee?",
        "Everything related to the user's work projects and deadlines".

        Args:
            question: The question to answer, in natural language.

        Returns:
            List of matching memories ranked by relevance.
        """
        if not question or not question.strip():
            return json.dumps({"error": True, "message": "Question cannot be empty"})

        if __event_emitter__:
            await __event_emitter__(
                {"type": "status", "data": {"description": "Deep searching memories...", "done": False}}
            )

        result = await self._post(
            "/api/memories/find",
            {"question": question, "limit": 10},
            __user__,
        )

        if __event_emitter__:
            if result.get("error"):
                desc = f"Search error: {result.get('detail') or result.get('message', 'unknown')}"
            else:
                count = len(result.get("results", []))
                desc = f"Found {count} memories" if count else "No matching memories found"
            await __event_emitter__(
                {"type": "status", "data": {"description": desc, "done": True}}
            )

        return json.dumps(result, default=str)

    # ── Tool: update_memory ───────────────────────────────────────────

    async def update_memory(
        self,
        memory_id: str,
        content: str,
        __user__: dict = {},
        __event_emitter__: Optional[Callable] = None,
    ) -> str:
        """Update an existing memory's content. Use search_memory first to find the memory ID.

        Args:
            memory_id: The ID of the memory to update (from search results).
            content: The new content for this memory (max 1000 chars).

        Returns:
            Confirmation or error message.
        """
        if not memory_id or not memory_id.strip():
            return json.dumps({"error": True, "message": "memory_id is required"})
        if not content or not content.strip():
            return json.dumps({"error": True, "message": "content is required"})
        if len(content) > 1000:
            return json.dumps(
                {"error": True, "message": f"Content too long ({len(content)} chars, max 1000)"}
            )

        if __event_emitter__:
            await __event_emitter__(
                {"type": "status", "data": {"description": "Updating memory...", "done": False}}
            )

        result = await self._put(
            f"/api/memories/{memory_id}",
            {"content": content},
            __user__,
        )

        if __event_emitter__:
            if result.get("error"):
                desc = f"Update error: {result.get('detail') or result.get('message', 'unknown')}"
            else:
                desc = "Memory updated"
            await __event_emitter__(
                {"type": "status", "data": {"description": desc, "done": True}}
            )

        return json.dumps(result, default=str)

    # ── Tool: delete_memory ───────────────────────────────────────────

    async def delete_memory(
        self,
        memory_id: str,
        __user__: dict = {},
        __event_emitter__: Optional[Callable] = None,
    ) -> str:
        """Delete a memory permanently. Use search_memory first to find the memory ID.

        Args:
            memory_id: The ID of the memory to delete (from search results).

        Returns:
            Confirmation or error message.
        """
        if not memory_id or not memory_id.strip():
            return json.dumps({"error": True, "message": "memory_id is required"})

        if __event_emitter__:
            await __event_emitter__(
                {"type": "status", "data": {"description": "Deleting memory...", "done": False}}
            )

        result = await self._delete(
            f"/api/memories/{memory_id}",
            __user__,
        )

        if __event_emitter__:
            if result.get("error"):
                desc = f"Delete error: {result.get('detail') or result.get('message', 'unknown')}"
            else:
                desc = "Memory deleted"
            await __event_emitter__(
                {"type": "status", "data": {"description": desc, "done": True}}
            )

        return json.dumps(result, default=str)
