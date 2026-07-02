from __future__ import annotations

import asyncio
from playwright.async_api import async_playwright
from markdownify import markdownify as md

from fastmcp import FastMCP

mcp = FastMCP("Mission Tools")


@mcp.tool
async def web_fetch(url: str) -> dict:
    """Fetch a web page and return its main content as Markdown. Timeout: 20s."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage", "--no-sandbox"],
            )
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                await asyncio.sleep(1)  # let JS settle
                html = await page.content()
                text = md(html)
                return {"ok": True, "markdown": text[:50_000]}
            finally:
                await browser.close()
    except asyncio.TimeoutError:
        return {"ok": False, "error": "timeout: page took longer than 20s"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def create_app():
    """Return the ASGI app for the MCP server."""
    return mcp.http_app()
