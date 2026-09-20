import json
from pydantic import BaseModel
from typing import Any
import requests
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
import ollama
from helpers.llm_utils import clean_llm_json
from helpers.agent_trace import traced_call
from dotenv import load_dotenv
import os

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

class DirectAnswer(BaseModel):
    answer: Any
    reasoning: str
    confidence: float

def scrape_page(url: str) -> str:
    """Scrape the main text from a web page using requests + BeautifulSoup"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text() for p in paragraphs)
        return text[:5000]  # limit to 5000 chars for LLM
    except Exception as e:
        return f"ERROR: {e}"

def summarize_content(title: str, url: str, content: str) -> str:
    """Summarise scraped content using gemma3:4b LLM"""
    prompt = f"""
You are an expert summarizer. Summarise the following web page content in 2-3 concise sentences:

Title: {title}
URL: {url}
Content: {content}

Return strictly plain text summary.
"""
    try:
        response = ollama.chat(
            model="gemma3:4b",
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response["message"]["content"].strip()
        return summary
    except Exception:
        return "Unable to summarise content."

def web_scrape(query: str) -> DirectAnswer:
    """Fetch top 3 Google results, scrape, and summarise each page"""
    # Step 1: Fetch top 3 results from SerpAPI
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": 3
    }
    search = GoogleSearch(params)
    results = traced_call("Research Agent", "api_call / Google Search", search.get_dict)
    organic_results = results.get("organic_results", [])[:3]

    if not organic_results:
        return DirectAnswer(
            answer=[],
            reasoning=f"No results found for '{query}'",
            confidence=0.0
        )

    # Step 2: Scrape and summarise each page
    scraped_results = []
    for res in organic_results:
        url = res.get("link")
        title = res.get("title")
        snippet = res.get("snippet")

        content = traced_call("Research Agent", f"web_scrape / {url}", scrape_page, url)
        summary = traced_call("Research Agent", f"LLM summary / {title}", summarize_content, title, url, content) if not content.startswith("ERROR") else ""

        scraped_results.append({
            "title": title,
            "url": url,
            "snippet": snippet,
            "content": summary,
            "error": content if content.startswith("ERROR") else None
        })

    reasoning = f"Fetched, scraped, and summarised top {len(scraped_results)} Google search results for '{query}'."
    confidence = 0.9

    return DirectAnswer(
        answer=scraped_results,
        reasoning=reasoning,
        confidence=confidence
    )

# Example usage
if __name__ == "__main__":
    result = web_scrape("Recent trends in the energy sector")
    print(json.dumps(result.dict(), indent=2, ensure_ascii=False))
