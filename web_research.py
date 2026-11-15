import os
from urllib.parse import urlsplit
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()


def research_claim(claim: str) -> dict:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("Tavily API key is missing. Set TAVILY_API_KEY in .env.")
    try:
        response = TavilyClient(api_key=api_key).search(query=f"Current and reliable information about: {claim}", search_depth="basic", max_results=5, include_answer=True)
        results = []
        for item in response.get("results") or []:
            if not isinstance(item, dict) or not isinstance(item.get("url"), str):
                continue
            parsed_url = urlsplit(item["url"])
            if parsed_url.scheme in {"http", "https"} and parsed_url.netloc:
                results.append({"title": str(item.get("title") or "Source"), "url": item["url"], "content": str(item.get("content") or ""), "score": item.get("score")})
        return {"claim": claim, "search_answer": str(response.get("answer") or ""), "sources": results}
    except Exception as error:
        raise RuntimeError("Tavily research failed. Check the service, network connection, and TAVILY_API_KEY configuration.") from error

