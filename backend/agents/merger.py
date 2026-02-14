from backend.agents.base import BaseAgent
from backend.models.product import ExtractedProduct, MergedProduct, ProductVariant


MERGER_SYSTEM_PROMPT = """You are a product data merging expert. You will receive product data from multiple sources (original scraped data, Amazon Japan, Rakuten, vendor websites, etc.).

Your job is to:
1. Merge all data into ONE complete product profile
2. Use the BEST/MOST ACCURATE information from each source
3. Combine all images from all sources
4. Identify and group product variants (size, color, flavor, count variations)
5. Merge all specifications, ingredients, and certifications
6. Combine review summaries from all sources

RULES:
- If sources conflict, prefer the most detailed/specific source
- Combine all images (deduplicated)
- Merge all specs into one comprehensive dict
- List ALL ingredients found across sources
- List ALL certifications found across sources
- Identify variants if multiple exist

Return a JSON object with:
{
    "merged_title": "best product title",
    "merged_description": "most complete description",
    "brand": "brand name",
    "all_images": ["url1", "url2"],
    "price_range": "price range across sources or null",
    "weight": "product weight or null",
    "dimensions": "dimensions or null",
    "ingredients": ["ingredient1", "ingredient2"],
    "certifications": ["cert1", "cert2"],
    "reviews_summary": "combined review summary",
    "variants": [{"name": "variant name", "specs": {}}],
    "all_specs": {"key": "value"},
    "sources_used": ["amazon_japan", "rakuten", etc],
    "rating": "best available rating or null",
    "review_count": "total reviews or null",
    "monthly_sales": "monthly sales figure if found or null"
}"""


class MergerAgent(BaseAgent):
    """Agent 4: Merges product data from all sources into one complete profile."""

    name = "merger"

    async def run(self, input_data: ExtractedProduct) -> MergedProduct:
        """Merge all extracted source data into one product profile.

        Args:
            input_data: ExtractedProduct with data from multiple sources.

        Returns:
            MergedProduct with all data merged.
        """
        extracted = input_data

        if not self.llm:
            raise RuntimeError("MergerAgent requires an LLM provider")

        # Build the prompt with all source data
        sources_text = f"""ORIGINAL SCRAPED DATA:
Title: {extracted.raw.title}
Brand: {extracted.raw.brand}
Description: {extracted.raw.description}
Price: {extracted.raw.price or 'N/A'}
Images: {', '.join(extracted.raw.images) if extracted.raw.images else 'None'}
Extra Fields: {extracted.raw.extra_fields}
"""

        for i, source in enumerate(extracted.sources, 1):
            sources_text += f"""
--- SOURCE {i}: {source.source} ({source.url}) ---
Title: {source.title}
Description: {source.description}
Price: {source.price or 'N/A'}
Weight: {source.weight or 'N/A'}
Dimensions: {source.dimensions or 'N/A'}
Images: {len(source.images)} images
Specs: {source.specs}
Ingredients: {source.ingredients}
Certifications: {source.certifications}
Reviews: {source.reviews_summary or 'N/A'}
Rating: {source.rating or 'N/A'}
Review Count: {source.review_count or 'N/A'}
"""

        prompt = f"""Merge all the following product data into ONE complete product profile:

{sources_text}

Return a comprehensive merged JSON object."""

        try:
            data = await self.llm.generate_json(prompt, system_prompt=MERGER_SYSTEM_PROMPT)
        except Exception:
            # Fallback: use raw data if LLM fails
            data = {}

        # Collect all images from all sources
        all_images = list(extracted.raw.images)
        for source in extracted.sources:
            all_images.extend(source.images)
        all_images.extend(data.get("all_images", []))
        all_images = list(dict.fromkeys(all_images))  # Deduplicate

        # Build variants
        variants = []
        for v in data.get("variants", []):
            variants.append(ProductVariant(
                name=v.get("name", ""),
                specs=v.get("specs", {}),
            ))

        return MergedProduct(
            raw=extracted.raw,
            merged_title=data.get("merged_title", extracted.raw.title),
            merged_description=data.get("merged_description", extracted.raw.description),
            brand=data.get("brand", extracted.raw.brand),
            all_images=all_images,
            price_range=data.get("price_range"),
            weight=data.get("weight"),
            dimensions=data.get("dimensions"),
            ingredients=data.get("ingredients", []),
            certifications=data.get("certifications", []),
            reviews_summary=data.get("reviews_summary", ""),
            variants=variants,
            all_specs=data.get("all_specs", {}),
            sources_used=data.get("sources_used", [s.source for s in extracted.sources]),
            rating=data.get("rating"),
            review_count=data.get("review_count"),
            monthly_sales=data.get("monthly_sales"),
        )
