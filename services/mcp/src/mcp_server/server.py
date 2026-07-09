from __future__ import annotations

import asyncio

from fastmcp import FastMCP
from markdownify import markdownify as md
from playwright.async_api import async_playwright

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
    except TimeoutError:
        return {"ok": False, "error": "timeout: page took longer than 20s"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool
async def web_search(query: str, num_results: int = 5) -> dict:
    """Search Google and return top results with content. Timeout: 30s."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage", "--no-sandbox"],
            )
            try:
                search_page = await browser.new_page()
                search_url = f"https://www.google.com/search?q={query}&tbs=qdr:d"
                await search_page.goto(search_url, wait_until="domcontentloaded", timeout=20_000)
                await asyncio.sleep(2)
                results = await search_page.evaluate("""() => {
                    const items = document.querySelectorAll('div.g');
                    return Array.from(items).slice(0, 5).map(item => {
                        const titleEl = item.querySelector('h3');
                        const linkEl = item.querySelector('a');
                        const snippetEl = item.querySelector('div[data-sncf], div.VwiC3b');
                        return {
                            title: titleEl?.textContent || '',
                            url: linkEl?.href || '',
                            snippet: snippetEl?.textContent || '',
                        };
                    }).filter(r => r.url && r.title);
                }""")
                await search_page.close()

                async def fetch_page(r: dict) -> dict:
                    pg = await browser.new_page()
                    try:
                        await pg.goto(r["url"], wait_until="domcontentloaded", timeout=15_000)
                        await asyncio.sleep(1)
                        html = await pg.content()
                        return {
                            "title": r["title"],
                            "url": r["url"],
                            "snippet": r["snippet"],
                            "content": md(html)[:10_000],
                        }
                    except Exception:
                        return {
                            "title": r["title"],
                            "url": r["url"],
                            "snippet": r["snippet"],
                            "content": "",
                        }
                    finally:
                        await pg.close()

                enriched = await asyncio.gather(*[fetch_page(r) for r in results[:num_results]])
                return {"ok": True, "results": list(enriched)}
            finally:
                await browser.close()
    except TimeoutError:
        return {"ok": False, "error": "timeout: search took longer than 30s"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def create_app():
    """Return the ASGI app for the MCP server."""
    return mcp.http_app()
