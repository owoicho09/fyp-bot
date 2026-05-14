print("[search_service.py] Loading search service...")

import httpx
import asyncio
from typing import Optional

OPENALEX_BASE  = "https://api.openalex.org/works"
CROSSREF_BASE  = "https://api.crossref.org/works"
SEMANTIC_BASE  = "https://api.semanticscholar.org/graph/v1/paper/search"
OPENALEX_EMAIL = "fyp.mentor.bot@gmail.com"
TIMEOUT        = 20


# ─── OPENALEX ─────────────────────────────────────────────────────────────────

async def search_openalex(
    query: str,
    max_results: int = 5,
    year_from: int = 2019,
) -> list[dict]:
    """
    Search OpenAlex for verified academic papers.
    year_from filters to papers published from that year onwards.
    Default is 2019 (last ~5 years). Pass 1990 for no restriction.
    """
    print(f"[search] search_openalex: query='{query[:60]}' max={max_results} year_from={year_from}")

    # Build filter — always require DOI, optionally filter by year
    filter_parts = ["has_doi:true"]
    if year_from and year_from > 1990:
        filter_parts.append(f"publication_year:>{year_from - 1}")
    filter_str = ",".join(filter_parts)

    params = {
        "search":   query,
        "per-page": max_results,
        "select":   "id,title,authorships,publication_year,doi,primary_location,cited_by_count",
        "mailto":   OPENALEX_EMAIL,
        "filter":   filter_str,
        "sort":     "publication_year:desc",  # Most recent first
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(OPENALEX_BASE, params=params)
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        print(f"[search] OpenAlex returned {len(results)} results.")
        papers = [p for p in (_parse_openalex_result(r) for r in results) if p]
        print(f"[search] Parsed {len(papers)} valid papers from OpenAlex.")
        return papers

    except httpx.TimeoutException:
        print("[search] OpenAlex timed out.")
        return []
    except Exception as e:
        print(f"[search] OpenAlex error: {e}")
        return []


def _parse_openalex_result(item: dict) -> Optional[dict]:
    try:
        doi = (item.get("doi") or "").replace("https://doi.org/", "").strip()
        if not doi:
            return None
        title = (item.get("title") or "").strip()
        if not title:
            return None
        year        = item.get("publication_year")
        authorships = item.get("authorships", [])
        authors     = [
            a["author"]["display_name"]
            for a in authorships[:6]
            if a.get("author", {}).get("display_name")
        ]
        location = item.get("primary_location") or {}
        source   = location.get("source") or {}
        journal  = source.get("display_name", "")
        cited_by = item.get("cited_by_count", 0)
        return {
            "source":   "openalex",
            "title":    title,
            "authors":  authors,
            "year":     year,
            "journal":  journal,
            "doi":      doi,
            "url":      f"https://doi.org/{doi}",
            "cited_by": cited_by,
        }
    except Exception as e:
        print(f"[search] _parse_openalex_result error: {e}")
        return None


# ─── CROSSREF (FALLBACK 1) ────────────────────────────────────────────────────

async def search_crossref(
    query: str,
    max_results: int = 5,
    year_from: int = 2019,
) -> list[dict]:
    print(f"[search] search_crossref: query='{query[:60]}' max={max_results} year_from={year_from}")
    params = {
        "query":  query,
        "rows":   max_results,
        "select": "DOI,title,author,published,container-title,is-referenced-by-count",
    }
    if year_from and year_from > 1990:
        params["filter"] = f"from-pub-date:{year_from}"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(CROSSREF_BASE, params=params)
            response.raise_for_status()
            data = response.json()

        items  = data.get("message", {}).get("items", [])
        print(f"[search] Crossref returned {len(items)} results.")
        papers = [p for p in (_parse_crossref_result(r) for r in items) if p]
        print(f"[search] Parsed {len(papers)} valid papers from Crossref.")
        return papers

    except httpx.TimeoutException:
        print("[search] Crossref timed out.")
        return []
    except Exception as e:
        print(f"[search] Crossref error: {e}")
        return []


def _parse_crossref_result(item: dict) -> Optional[dict]:
    try:
        doi = (item.get("DOI") or "").strip()
        if not doi:
            return None
        titles = item.get("title", [])
        title  = titles[0].strip() if titles else ""
        if not title:
            return None
        published  = item.get("published", {})
        date_parts = published.get("date-parts", [[]])
        year       = date_parts[0][0] if date_parts and date_parts[0] else None
        authors_raw = item.get("author", [])
        authors = []
        for a in authors_raw[:6]:
            given  = a.get("given", "")
            family = a.get("family", "")
            name   = f"{given} {family}".strip() if given else family
            if name:
                authors.append(name)
        containers = item.get("container-title", [])
        journal    = containers[0] if containers else ""
        cited_by   = item.get("is-referenced-by-count", 0)
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

async def search_semantic_scholar(
    query: str,
    max_results: int = 5,
    year_from: int = 2019,
) -> list[dict]:
    print(f"[search] search_semantic_scholar: '{query[:60]}' year_from={year_from}")
    params = {
        "query":  query,
        "limit":  max_results,
        "fields": "title,authors,year,externalIds,journal,citationCount",
    }
    if year_from and year_from > 1990:
        params["year"] = f"{year_from}-"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(SEMANTIC_BASE, params=params)
            response.raise_for_status()
            data = response.json()

        items  = data.get("data", [])
        print(f"[search] Semantic Scholar returned {len(items)} results.")
        papers = [p for p in (_parse_semantic_result(r) for r in items) if p]
        print(f"[search] Parsed {len(papers)} valid papers from Semantic Scholar.")
        return papers

    except httpx.TimeoutException:
        print("[search] Semantic Scholar timed out.")
        return []
    except Exception as e:
        print(f"[search] Semantic Scholar error: {e}")
        return []


def _parse_semantic_result(item: dict) -> Optional[dict]:
    try:
        external_ids = item.get("externalIds") or {}
        doi = (external_ids.get("DOI") or "").strip()
        if not doi:
            return None
        title = (item.get("title") or "").strip()
        if not title:
            return None
        year        = item.get("year")
        authors_raw = item.get("authors", [])
        authors     = [a.get("name", "") for a in authors_raw[:6] if a.get("name")]
        journal_data = item.get("journal") or {}
        journal      = journal_data.get("name", "")
        cited_by     = item.get("citationCount", 0)
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


# ─── FULL FALLBACK CHAIN ──────────────────────────────────────────────────────

async def find_citations(
    query: str,
    max_results: int = 5,
    year_from: int = 2019,
) -> dict:
    """
    Run the full citation search chain for one query.
    OpenAlex → Crossref → Semantic Scholar.
    Passes year_from to all sources.
    """
    print(f"[search] find_citations: '{query[:60]}' year_from={year_from}")

    papers = await search_openalex(query, max_results, year_from)
    if papers:
        return {"papers": papers, "source": "openalex", "query": query}

    print("[search] OpenAlex empty — trying Crossref...")
    papers = await search_crossref(query, max_results, year_from)
    if papers:
        return {"papers": papers, "source": "crossref", "query": query}

    print("[search] Crossref empty — trying Semantic Scholar...")
    papers = await search_semantic_scholar(query, max_results, year_from)
    if papers:
        return {"papers": papers, "source": "semantic_scholar", "query": query}

    print(f"[search] All sources exhausted for: '{query[:60]}'")
    return {"papers": [], "source": "none", "query": query}


async def find_citations_batch(
    queries: list[str],
    max_per_query: int = 5,
    year_from: int = 2019,
) -> list[dict]:
    """
    Run find_citations for multiple queries concurrently.
    Returns flat list of unique papers across all queries.
    year_from passed through to every search.
    """
    print(f"[search] find_citations_batch: {len(queries)} queries year_from={year_from}")
    tasks   = [find_citations(q, max_per_query, year_from) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_papers = []
    seen_dois  = set()
    for result in results:
        if isinstance(result, Exception):
            print(f"[search] Batch exception: {result}")
            continue
        for paper in result.get("papers", []):
            doi = paper.get("doi", "")
            if doi and doi not in seen_dois:
                seen_dois.add(doi)
                all_papers.append(paper)

    print(f"[search] Batch complete. {len(all_papers)} unique papers.")
    return all_papers


# ─── NIGERIAN STATISTICS ──────────────────────────────────────────────────────

async def search_nigerian_stats(topic: str) -> dict:
    """Fetch live Nigerian statistics from World Bank API."""
    print(f"[search] search_nigerian_stats: topic='{topic[:60]}'")
    stats = {}
    wb_queries = [
        ("gdp_growth",   "NY.GDP.MKTP.KD.ZG", "GDP growth rate"),
        ("inflation",    "FP.CPI.TOTL.ZG",    "Inflation rate"),
        ("unemployment", "SL.UEM.TOTL.ZS",    "Unemployment rate"),
        ("poverty_rate", "SI.POV.NAHC",        "Poverty headcount ratio"),
        ("population",   "SP.POP.TOTL",        "Total population"),
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
                        isinstance(data, list) and len(data) > 1
                        and data[1] and data[1][0].get("value") is not None
                    ):
                        value = data[1][0]["value"]
                        year  = data[1][0].get("date", "")
                        stats[key] = {
                            "label":  label,
                            "value":  round(float(value), 2),
                            "year":   year,
                            "source": "World Bank Nigeria",
                        }
                        print(f"[search] World Bank stat: {label}={value} ({year})")
                except Exception as e:
                    print(f"[search] World Bank {label} error: {e}")
                    continue
    except Exception as e:
        print(f"[search] World Bank block error: {e}")

    print(f"[search] search_nigerian_stats complete. {len(stats)} stats found.")
    return stats


def format_stats_for_prompt(stats: dict) -> str:
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