from pathlib import Path
from backend.agents.base import BaseAgent
from backend.models.product import MergedProduct, ShopifyProduct
from backend.config import settings


class CopywriterAgent(BaseAgent):
    """Agent 5: Generates 15 Shopify product sections using copywriting rules and AI."""

    name = "copywriter"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Load the copywriter system prompt
        prompt_path = settings.PROMPTS_DIR / "copywriter.txt"
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    async def run(self, input_data: MergedProduct) -> ShopifyProduct:
        """Generate all 15 Shopify sections for a product.

        Args:
            input_data: MergedProduct with all enriched data.

        Returns:
            ShopifyProduct with all 15 sections filled.
        """
        merged = input_data

        if not self.llm:
            raise RuntimeError("CopywriterAgent requires an LLM provider")

        # Build the product data prompt
        prompt = self._build_prompt(merged)

        # Generate copy
        try:
            data = await self.llm.generate_json(prompt, system_prompt=self.system_prompt)
        except Exception as e:
            raise RuntimeError(f"Copywriter LLM call failed: {e}")

        return ShopifyProduct(
            title=data.get("title", ""),
            description=data.get("description", ""),
            usps=data.get("usps", []),
            specifications=data.get("specifications", ""),
            who_is_this_for=data.get("who_is_this_for", []),
            benefits=data.get("benefits", []),
            features=data.get("features", []),
            whats_inside=data.get("whats_inside", ""),
            how_to_use=data.get("how_to_use", ""),
            product_story=data.get("product_story", ""),
            ingredients=data.get("ingredients", []),
            certifications=data.get("certifications", []),
            about_brand=data.get("about_brand", ""),
            shipping=data.get("shipping", "Your order departs from Japan in 3 days and will be delivered worldwide in 9~12 days. Shipping is just $5, sent directly to your home."),
            sold_in_stores=data.get("sold_in_stores", []),
        )

    def _build_prompt(self, merged: MergedProduct) -> str:
        """Build the product data prompt for the copywriter."""

        variants_text = ""
        if merged.variants:
            variants_text = "\nVARIANTS:\n"
            for v in merged.variants:
                variants_text += f"- {v.name}: {v.specs}\n"

        specs_text = ""
        if merged.all_specs:
            specs_text = "\nSPECIFICATIONS:\n"
            for k, v in merged.all_specs.items():
                specs_text += f"- {k}: {v}\n"

        return f"""Write complete Shopify product copy for this product. Return JSON with all 15 sections.

PRODUCT DATA:
Title: {merged.merged_title}
Brand: {merged.brand}
Description: {merged.merged_description}

IMAGES: {len(merged.all_images)} product images available
PRICE RANGE: {merged.price_range or 'N/A'}
WEIGHT: {merged.weight or 'N/A'}
DIMENSIONS: {merged.dimensions or 'N/A'}

INGREDIENTS: {', '.join(merged.ingredients) if merged.ingredients else 'N/A'}
CERTIFICATIONS: {', '.join(merged.certifications) if merged.certifications else 'N/A'}

REVIEWS SUMMARY: {merged.reviews_summary or 'N/A'}
RATING: {merged.rating or 'N/A'}
REVIEW COUNT: {merged.review_count or 'N/A'}
MONTHLY SALES: {merged.monthly_sales or 'N/A'}

SOURCES USED: {', '.join(merged.sources_used)}
{variants_text}
{specs_text}

EXTRA DATA: {merged.raw.extra_fields}

Generate ALL 15 sections following the exact format specified. Return as a JSON object with keys: title, description, usps, specifications, who_is_this_for, benefits, features, whats_inside, how_to_use, product_story, ingredients, certifications, about_brand, shipping, sold_in_stores."""
