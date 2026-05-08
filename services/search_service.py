print("[search_service.py] Loading search service...")

import httpx
import asyncio
from typing import Optional

# ─── API ENDPOINTS ────────────────────────────────────────────────────────────
OPENALEX_BASE      = "https://api.openalex.org/works"
CROSSREF_BASE      = "https://api.crossref.org/works"
SEMANTIC_BASE      = "https://api.semanticscholar.org/graph/v1/paper/search"

# Polite pool email for OpenAlex (improves rate limits — no key needed)
OPENALEX_EMAIL     = "fyp.mentor.bot@gmail.com"

# Request timeout in seconds
TIMEOUT            = 20


# ─── OPENALEX ─────────────────────────────────────────────────────────────────

async def search_openalex(query: str, max_results: int = 5) -> list[dict]:
    """
    Search OpenAlex for verified academic papers matching a query.
    Returns a list of clean citation dicts with confirmed DOIs.
    OpenAlex indexes 250M+ works — no API key required.
    """
    print(f"[search] search_openalex: query='{query[:60]}' max={max_results}")
    params = {
        "search":     query,
        "per-page":   max_results,
        "select":     "id,title,authorships,publication_year,doi,primary_location,cited_by_count",
        "mailto":     OPENALEX_EMAIL,
        "filter":     "has_doi:true",   # Only return papers with confirmed DOIs
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(OPENALEX_BASE, params=params)
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        print(f"[search] OpenAlex returned {len(results)} results.")
        papers = []
        for item in results:
            paper = _parse_openalex_result(item)
            if paper:
                papers.append(paper)
        print(f"[search] Parsed {len(papers)} valid papers from OpenAlex.")
        return papers

    except httpx.TimeoutException:
        print("[search] OpenAlex request timed out.")
        return []
    except Exception as e:
        print(f"[search] OpenAlex error: {e}")
        return []


def _parse_openalex_result(item: dict) -> Optional[dict]:
    """Parse a single OpenAlex work into a clean citation dict."""
    try:
        doi = item.get("doi", "")
        if not doi:
            return None
        # Clean DOI — OpenAlex returns full URL format
        doi = doi.replace("https://doi.org/", "").strip()

        title = item.get("title", "").strip()
        if not title:
            return None

        year = item.get("publication_year")

        # Extract authors
        authorships = item.get("authorships", [])
        authors = []
        for a in authorships[:6]:   # Max 6 authors
            author = a.get("author", {})
            name = author.get("display_name", "")
            if name:
                authors.append(name)

        # Extract journal/source
        location = item.get("primary_location", {}) or {}
        source = location.get("source", {}) or {}
        journal = source.get("display_name", "")

        cited_by = item.get("cited_by_count", 0)

        return {
            "source":     "openalex",
            "title":      title,
            "authors":    authors,
            "year":       year,
            "journal":    journal,
            "doi":        doi,
            "url":        f"https://doi.org/{doi}",
            "cited_by":   cited_by,
        }
    except Exception as e:
        print(f"[search] _parse_openalex_result error: {e}")
        return None


# ─── CROSSREF (FALLBACK 1) ────────────────────────────────────────────────────

async def search_crossref(query: str, max_results: int = 5) -> list[dict]:
    """
    Fallback to Crossref if OpenAlex returns nothing.
    Crossref indexes 140M+ works. No API key required.
    """
    print(f"[search] search_crossref: query='{query[:60]}' max={max_results}")
    params = {
        "query":  query,
        "rows":   max_results,
        "select": "DOI,title,author,published,container-title,is-referenced-by-count",
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(CROSSREF_BASE, params=params)
            response.raise_for_status()
            data = response.json()

        items = data.get("message", {}).get("items", [])
        print(f"[search] Crossref returned {len(items)} results.")
        papers = []
        for item in items:
            paper = _parse_crossref_result(item)
            if paper:
                papers.append(paper)
        print(f"[search] Parsed {len(papers)} valid papers from Crossref.")
        return papers

    except httpx.TimeoutException:
        print("[search] Crossref request timed out.")
        return []
    except Exception as e:
        print(f"[search] Crossref error: {e}")
        return []


def _parse_crossref_result(item: dict) -> Optional[dict]:
    """Parse a single Crossref item into a clean citation dict."""
    try:
        doi = item.get("DOI", "").strip()
        if not doi:
            return None

        titles = item.get("title", [])
        title = titles[0].strip() if titles else ""
        if not title:
            return None

        # Extract year
        published = item.get("published", {})
        date_parts = published.get("date-parts", [[]])
        year = date_parts[0][0] if date_parts and date_parts[0] else None

        # Extract authors
        authors_raw = item.get("author", [])
        authors = []
        for a in authors_raw[:6]:
            given  = a.get("given", "")
            family = a.get("family", "")
            name   = f"{given} {family}".strip() if given else family
            if name:
                authors.append(name)

        # Journal
        containers = item.get("container-title", [])
        journal = containers[0] if containers else ""

        cited_by = item.get("is-referenced-by-count", 0)

        return {
            "source":   "crossref",
            "title":    title,
            "authors":  authors,
            "year":     year,
            "journal":  journal,
            "doi":      doi,
            "url":      f"https://doi.org/{doi}",
            "cited_by": cited_by,
        }
    except Exception as e:
        print(f"[search] _parse_crossref_result error: {e}")
        return None


# ─── SEMANTIC SCHOLAR (FALLBACK 2) ────────────────────────────────────────────

async def search_semantic_scholar(query: str, max_results: int = 5) -> list[dict]:
    """
    Final fallback — Semantic Scholar.
    Free, no API key required for basic search.
    """
    print(f"[search] search_semantic_scholar: query='{query[:60]}' max={max_results}")
    params = {
        "query":  query,
        "limit":  max_results,
        "fields": "title,authors,year,externalIds,journal,citationCount",
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(SEMANTIC_BASE, params=params)
            response.raise_for_status()
            data = response.json()

        items = data.get("data", [])
        print(f"[search] Semantic Scholar returned {len(items)} results.")
        papers = []
        for item in items:
            paper = _parse_semantic_result(item)
            if paper:
                papers.append(paper)
        print(f"[search] Parsed {len(papers)} valid papers from Semantic Scholar.")
        return papers

    except httpx.TimeoutException:
        print("[search] Semantic Scholar request timed out.")
        return []
    except Exception as e:
        print(f"[search] Semantic Scholar error: {e}")
        return []


def _parse_semantic_result(item: dict) -> Optional[dict]:
    """Parse a single Semantic Scholar result into a clean citation dict."""
    try:
        external_ids = item.get("externalIds", {}) or {}
        doi = external_ids.get("DOI", "").strip()
        # Semantic Scholar papers without DOIs are less trustworthy — skip them
        if not doi:
            return None

        title = item.get("title", "").strip()
        if not title:
            return None

        year = item.get("year")

        authors_raw = item.get("authors", [])
        authors = [a.get("name", "") for a in authors_raw[:6] if a.get("name")]

        journal_data = item.get("journal", {}) or {}
        journal = journal_data.get("name", "")

        cited_by = item.get("citationCount", 0)

        return {
            "source":   "semantic_scholar",
            "title":    title,
            "authors":  authors,
            "year":     year,
            "journal":  journal,
            "doi":      doi,
            "url":      f"https://doi.org/{doi}",
            "cited_by": cited_by,
        }
    except Exception as e:
        print(f"[search] _parse_semantic_result error: {e}")
        return None


# ─── MAIN CITATION SEARCH (FULL FALLBACK CHAIN) ───────────────────────────────

async def find_citations(query: str, max_results: int = 5) -> dict:
    """
    Run the full citation fallback chain for a single query.
    OpenAlex → Crossref → Semantic Scholar.
    Returns:
        {
            "papers": [...],
            "source": "openalex" | "crossref" | "semantic_scholar" | "none",
            "query":  "the original query",
        }
    """
    print(f"[search] find_citations: '{query[:60]}'")

    papers = await search_openalex(query, max_results)
    if papers:
        return {"papers": papers, "source": "openalex", "query": query}

    print("[search] OpenAlex empty — trying Crossref...")
    papers = await search_crossref(query, max_results)
    if papers:
        return {"papers": papers, "source": "crossref", "query": query}

    print("[search] Crossref empty — trying Semantic Scholar...")
    papers = await search_semantic_scholar(query, max_results)
    if papers:
        return {"papers": papers, "source": "semantic_scholar", "query": query}

    print(f"[search] All sources exhausted for query: '{query[:60]}'")
    return {"papers": [], "source": "none", "query": query}


async def find_citations_batch(queries: list[str], max_per_query: int = 4) -> list[dict]:
    """
    Run find_citations for multiple queries concurrently.
    Used during Chapter 2 generation to fetch citations for all claims at once.
    Returns a flat list of all unique papers found across all queries.
    """
    print(f"[search] find_citations_batch: {len(queries)} queries")
    tasks = [find_citations(q, max_per_query) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_papers = []
    seen_dois = set()
    for result in results:
        if isinstance(result, Exception):
            print(f"[search] Batch query exception: {result}")
            continue
        for paper in result.get("papers", []):
            doi = paper.get("doi", "")
            if doi and doi not in seen_dois:
                seen_dois.add(doi)
                all_papers.append(paper)

    print(f"[search] Batch complete. {len(all_papers)} unique papers found.")
    return all_papers


# ─── NIGERIAN STATISTICS SEARCH ───────────────────────────────────────────────

async def search_nigerian_stats(topic: str) -> dict:
    """
    Search for current Nigerian statistics and data relevant to a topic.
    Uses httpx to query public Nigerian data sources directly.
    Returns a dict of found statistics for injection into chapter prompts.

    Currently queries:
    - NBS (National Bureau of Statistics) open data
    - World Bank Nigeria open data
    Falls back gracefully — Claude handles missing data with general knowledge.
    """
    print(f"[search] search_nigerian_stats: topic='{topic[:60]}'")
    stats = {}

    # World Bank Nigeria indicator search
    wb_queries = [
        ("gdp_growth",    "NY.GDP.MKTP.KD.ZG", "GDP growth rate"),
        ("inflation",     "FP.CPI.TOTL.ZG",    "Inflation rate"),
        ("unemployment",  "SL.UEM.TOTL.ZS",    "Unemployment rate"),
        ("poverty_rate",  "SI.POV.NAHC",        "Poverty headcount ratio"),
        ("population",    "SP.POP.TOTL",        "Total population"),
    ]

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for key, indicator, label in wb_queries:
                try:
                    url = (
                        f"https://api.worldbank.org/v2/country/NG/indicator/"
                        f"{indicator}?format=json&mrv=1&per_page=1"
                    )
                    r = await client.get(url)
                    r.raise_for_status()
                    data = r.json()
                    if (
                        isinstance(data, list)
                        and len(data) > 1
                        and data[1]
                        and data[1][0].get("value") is not None
                    ):
                        value = data[1][0]["value"]
                        year  = data[1][0].get("date", "")
                        stats[key] = {
                            "label": label,
                            "value": round(float(value), 2),
                            "year":  year,
                            "source": "World Bank Nigeria",
                        }
                        print(f"[search] World Bank stat: {label}={value} ({year})")
                except Exception as e:
                    print(f"[search] World Bank {label} fetch failed: {e}")
                    continue

    except Exception as e:
        print(f"[search] World Bank stats block failed: {e}")

    print(f"[search] search_nigerian_stats complete. {len(stats)} stats found.")
    return stats


def format_stats_for_prompt(stats: dict) -> str:
    """
    Format the fetched Nigerian statistics into a string for injection
    into the Claude system prompt.
    """
    if not stats:
        return "No live Nigerian statistics fetched — use CBN/NBS general knowledge."

    lines = ["LIVE NIGERIAN STATISTICS (fetched at generation time):"]
    for key, stat in stats.items():
        lines.append(
            f"- {stat['label']}: {stat['value']}% "
            f"({stat['year']}, Source: {stat['source']})"
        )
    return "\n".join(lines)


print("[search_service.py] Search service loaded.")