"""
Research engine using Tavily API.
Dynamic query generation based on campaign profile.
Company pain-point focused. Industry fallback guaranteed.
"""

from tavily import TavilyClient
import streamlit as st
from datetime import datetime


def get_tavily_client():
    api_key = st.secrets.get("TAVILY_API_KEY", "")
    if not api_key:
        return None
    return TavilyClient(api_key=api_key)


def _search(client, query, label):
    """Run a single Tavily search and return structured result."""
    try:
        results = client.search(query=query, max_results=5, search_depth="advanced")
        return {
            "source": label,
            "query": query,
            "results": results.get("results", []),
            "status": "success",
            "count": len(results.get("results", [])),
        }
    except Exception as e:
        return {
            "source": label,
            "query": query,
            "results": [],
            "status": "error",
            "error": str(e),
            "count": 0,
        }


def find_prospects_via_linkedin(client, company_name, target_titles):
    """Search LinkedIn via Tavily to find relevant people at a company."""
    all_people = []
    titles = [t.strip() for t in target_titles.split(",") if t.strip()][:3]
    for title in titles:
        result = _search(
            client,
            f'site:linkedin.com "{company_name}" "{title}"',
            f"LinkedIn Search: {title}",
        )
        if result["results"]:
            for r in result["results"]:
                all_people.append({
                    "title_searched": title,
                    "result_title": r.get("title", ""),
                    "snippet": r.get("content", "")[:300],
                    "url": r.get("url", ""),
                })
    return all_people


def run_research_with_queries(generated_queries, prospect_name=None, company_name=""):
    """
    Execute research using AI-generated queries.
    Takes the structured queries from Groq and runs them through Tavily.
    """
    client = get_tavily_client()
    if not client:
        return None

    all_results = []
    company_count = 0
    prospect_count = 0
    industry_count = 0

    # TIER 1: Company + Pain Point queries
    tier1_queries = generated_queries.get("tier1_pain_point", [])
    for q in tier1_queries:
        result = _search(client, q, "Company + Pain Point")
        all_results.append(result)
        company_count += result["count"]

    # TIER 2: Company + Leadership / Prospect verification
    tier2_queries = generated_queries.get("tier2_leadership", [])
    for q in tier2_queries:
        result = _search(client, q, "Leadership & Prospect Search")
        all_results.append(result)
        company_count += result["count"]

    # TIER 3: Industry + Pain Point (ALWAYS runs)
    tier3_queries = generated_queries.get("tier3_industry", [])
    for q in tier3_queries:
        result = _search(client, q, "Industry Trends")
        all_results.append(result)
        industry_count += result["count"]

    # TIER 4: Prospect + Topic (only if prospect provided)
    if prospect_name:
        tier4_queries = generated_queries.get("tier4_prospect", [])
        for q in tier4_queries:
            result = _search(client, q, "Prospect + Topic")
            all_results.append(result)
            prospect_count += result["count"]

    # Custom source if provided
    custom_queries = generated_queries.get("custom_source", [])
    for q in custom_queries:
        result = _search(client, q, "Custom Source")
        all_results.append(result)
        company_count += result["count"]

    total = sum(r["count"] for r in all_results)
    success = sum(1 for r in all_results if r["status"] == "success")

    return {
        "company_name": company_name,
        "prospect_name": prospect_name or "Not specified",
        "research_sources": all_results,
        "company_results_count": company_count,
        "prospect_results_count": prospect_count,
        "industry_results_count": industry_count,
        "total_results": total,
        "successful_sources": success,
        "total_sources": len(all_results),
        "tier1_had_results": company_count > 0,
        "timestamp": datetime.now().isoformat(),
    }
