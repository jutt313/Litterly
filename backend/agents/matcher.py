import json
from backend.agents.base import BaseAgent
from backend.models.product import RawProduct, MatchResult, MatchedProduct
from backend.search.duckduckgo import search_product_on_sites, SearchResult


MATCHER_SYSTEM_PROMPT = """You are a product matching expert. Your job is to analyze search results and determine which ones are the EXACT same product (and exact variant) as the original product.

IMPORTANT RULES:
- Match must be the EXACT same product, not just similar
- Match must be the EXACT same variant (size, color, flavor, count, etc.)
- Do NOT match bundles if the original is a single product
- Consider: title, brand, description, images, variant details
- Products can be listed on Amazon Japan (amazon.co.jp), Rakuten (rakuten.co.jp), or vendor websites

For each search result, decide if it's a match and give a confidence score (0.0 to 1.0).
Only include results with confidence >= 0.7"""


class MatcherAgent(BaseAgent):
    """Agent 2: Searches online and finds exact product matches using DuckDuckGo + AI verification."""

    name = "matcher"

    async def run(self, input_data: RawProduct) -> MatchedProduct:
        """Search for the product online and verify matches with AI.

        Args:
            input_data: A single RawProduct to match.

        Returns:
            MatchedProduct with verified match URLs.
        """
        product = input_data

        # Search DuckDuckGo across target sites
        search_results = await search_product_on_sites(
            product_title=product.title,
            brand=product.brand,
            sites=["amazon.co.jp", "rakuten.co.jp"],
            max_results=8,
        )

        if not search_results:
            return MatchedProduct(raw=product, matches=[])

        # Ask AI to verify which results match
        matches = await self._verify_matches(product, search_results)

        return MatchedProduct(raw=product, matches=matches)

    async def _verify_matches(
        self, product: RawProduct, search_results: list[SearchResult]
    ) -> list[MatchResult]:
        """Use LLM to verify which search results match the product."""
        if not self.llm:
            raise RuntimeError("MatcherAgent requires an LLM provider")

        # Format search results for the LLM
        results_text = ""
        for i, r in enumerate(search_results, 1):
            results_text += f"\n--- Result {i} ---\nTitle: {r.title}\nURL: {r.url}\nSnippet: {r.snippet}\n"

        prompt = f"""ORIGINAL PRODUCT:
Title: {product.title}
Brand: {product.brand}
Description: {product.description}
Price: {product.price or 'N/A'}

SEARCH RESULTS:
{results_text}

Analyze each search result. Return a JSON object with a "matches" array.
Each match should have: "result_index" (1-based), "source" (amazon_japan/rakuten/vendor_site/other), "url", "confidence" (0.0-1.0), "match_reason" (why this matches).

Only include results with confidence >= 0.7. If no results match, return {{"matches": []}}."""

        try:
            data = await self.llm.generate_json(prompt, system_prompt=MATCHER_SYSTEM_PROMPT)
        except Exception:
            return []

        matches = []
        for m in data.get("matches", []):
            idx = m.get("result_index", 0) - 1
            if 0 <= idx < len(search_results):
                matches.append(MatchResult(
                    source=m.get("source", "other"),
                    url=m.get("url", search_results[idx].url),
                    title=search_results[idx].title,
                    confidence=float(m.get("confidence", 0)),
                    match_reason=m.get("match_reason", ""),
                ))

        return matches
