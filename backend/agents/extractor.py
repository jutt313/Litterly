from backend.agents.base import BaseAgent
from backend.models.product import MatchedProduct, ExtractedProduct, SourceData
from backend.scraper.page_scraper import scrape_page


EXTRACTOR_SYSTEM_PROMPT = """You are a product data extraction expert. You will be given the raw text content of a product page. Extract all product information you can find.

Return a JSON object with these fields:
{
    "title": "product title",
    "description": "full product description",
    "price": "price with currency or null",
    "weight": "product weight or null",
    "dimensions": "product dimensions or null",
    "images": ["image_url_1", "image_url_2"],
    "specs": {"key": "value pairs of any specifications found"},
    "reviews_summary": "summary of customer reviews if found, or null",
    "ingredients": ["ingredient 1", "ingredient 2"],
    "certifications": ["certification 1", "certification 2"],
    "rating": "star rating if found or null",
    "review_count": "number of reviews if found or null"
}

Extract EVERYTHING available. Be thorough. If a field is not found, use null or empty array."""


class ExtractorAgent(BaseAgent):
    """Agent 3: Scrapes matched product pages and extracts structured data using AI."""

    name = "extractor"

    async def run(self, input_data: MatchedProduct) -> ExtractedProduct:
        """Scrape matched URLs and extract product data.

        Args:
            input_data: MatchedProduct with URLs to scrape.

        Returns:
            ExtractedProduct with all source data.
        """
        matched = input_data
        sources = []

        for match in matched.matches:
            # Scrape the page
            page = await scrape_page(match.url)

            if not page.success:
                continue

            # Use AI to extract structured data from page content
            source_data = await self._extract_from_page(match.source, match.url, page.text_content, page.images)
            if source_data:
                sources.append(source_data)

        return ExtractedProduct(
            raw=matched.raw,
            matches=matched.matches,
            sources=sources,
        )

    async def _extract_from_page(
        self, source: str, url: str, text_content: str, page_images: list[str]
    ) -> SourceData | None:
        """Use LLM to extract structured product data from page content."""
        if not self.llm:
            raise RuntimeError("ExtractorAgent requires an LLM provider")

        prompt = f"""Extract all product information from this page content:

URL: {url}
SOURCE: {source}

PAGE CONTENT:
{text_content[:12000]}

Return a JSON object with: title, description, price, weight, dimensions, images, specs, reviews_summary, ingredients, certifications, rating, review_count."""

        try:
            data = await self.llm.generate_json(prompt, system_prompt=EXTRACTOR_SYSTEM_PROMPT)
        except Exception:
            return None

        # Merge page images with any found in content
        all_images = list(set(page_images + data.get("images", [])))

        return SourceData(
            source=source,
            url=url,
            title=data.get("title", ""),
            description=data.get("description", ""),
            price=data.get("price"),
            weight=data.get("weight"),
            dimensions=data.get("dimensions"),
            images=all_images,
            specs=data.get("specs", {}),
            reviews_summary=data.get("reviews_summary"),
            ingredients=data.get("ingredients", []),
            certifications=data.get("certifications", []),
            rating=data.get("rating"),
            review_count=data.get("review_count"),
        )
