from dataclasses import dataclass
from duckduckgo_search import DDGS


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


async def search_product(query: str, max_results: int = 10) -> list[SearchResult]:
    """Search DuckDuckGo for a product.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        List of SearchResult objects.
    """
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                ))
    except Exception:
        # DuckDuckGo can sometimes rate limit, return what we have
        pass

    return results


async def search_product_on_sites(
    product_title: str,
    brand: str = "",
    sites: list[str] | None = None,
    max_results: int = 10,
) -> list[SearchResult]:
    """Search for a product across specific sites.

    Args:
        product_title: Product title to search for.
        brand: Brand name to include in search.
        sites: List of site domains to search (e.g., ["amazon.co.jp", "rakuten.co.jp"]).
        max_results: Max results per site.

    Returns:
        Combined list of SearchResult from all sites.
    """
    if sites is None:
        sites = ["amazon.co.jp", "rakuten.co.jp"]

    all_results = []
    search_base = f"{brand} {product_title}".strip()

    # Search each site specifically
    for site in sites:
        query = f"{search_base} site:{site}"
        results = await search_product(query, max_results=max_results)
        all_results.extend(results)

    # Also do a general search to find vendor/other sites
    general_results = await search_product(search_base, max_results=max_results)
    all_results.extend(general_results)

    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for r in all_results:
        if r.url not in seen_urls:
            seen_urls.add(r.url)
            unique_results.append(r)

    return unique_results
