import re
from backend.agents.base import BaseAgent
from backend.models.product import MergedProduct, ShopifyProduct, ExportRow


class ExporterAgent(BaseAgent):
    """Agent 6: Formats ShopifyProduct into Matrixify-compatible export row."""

    name = "exporter"

    async def run(self, input_data: tuple[MergedProduct, ShopifyProduct]) -> ExportRow:
        """Convert ShopifyProduct into a Matrixify CSV row.

        Args:
            input_data: Tuple of (MergedProduct, ShopifyProduct).

        Returns:
            ExportRow ready for CSV export.
        """
        merged, shopify = input_data

        # Build body HTML from all sections
        body_html = self._build_body_html(shopify)

        # Generate handle from title
        handle = self._slugify(shopify.title)

        return ExportRow(
            handle=handle,
            title=shopify.title,
            body_html=body_html,
            vendor=merged.brand,
            product_type="",
            tags="",
            variant_sku="",
            variant_weight=merged.weight or "",
            variant_weight_unit="g",
            image_src=merged.all_images[0] if merged.all_images else "",
            image_alt_text=shopify.title,
            seo_title=shopify.title,
            seo_description=shopify.description,
            metafield_usps="\n".join(shopify.usps),
            metafield_specifications=shopify.specifications,
            metafield_who_is_this_for="\n".join(shopify.who_is_this_for),
            metafield_benefits="\n".join(shopify.benefits),
            metafield_features="\n".join(shopify.features),
            metafield_whats_inside=shopify.whats_inside,
            metafield_how_to_use=shopify.how_to_use,
            metafield_product_story=shopify.product_story,
            metafield_ingredients="\n".join(shopify.ingredients),
            metafield_certifications="\n".join(shopify.certifications),
            metafield_about_brand=shopify.about_brand,
            metafield_shipping=shopify.shipping,
            metafield_sold_in_stores="\n".join(shopify.sold_in_stores),
        )

    def _build_body_html(self, shopify: ShopifyProduct) -> str:
        """Build the full HTML body for Shopify from all sections."""
        sections = []

        # Description
        if shopify.description:
            sections.append(f"<p>{shopify.description}</p>")

        # USPs
        if shopify.usps:
            usps_html = "".join(f"<li>{u}</li>" for u in shopify.usps)
            sections.append(f"<h3>Key Highlights</h3><ul>{usps_html}</ul>")

        # Who is this for
        if shopify.who_is_this_for:
            avatars_html = "".join(f"<li>{a}</li>" for a in shopify.who_is_this_for)
            sections.append(f"<h3>Who Is This For?</h3><ul>{avatars_html}</ul>")

        # Benefits
        if shopify.benefits:
            benefits_html = "".join(f"<li>{b}</li>" for b in shopify.benefits)
            sections.append(f"<h3>Your Benefits</h3><ul>{benefits_html}</ul>")

        # Features
        if shopify.features:
            features_html = "".join(f"<li>{f}</li>" for f in shopify.features)
            sections.append(f"<h3>Features</h3><ul>{features_html}</ul>")

        # What's Inside
        if shopify.whats_inside:
            sections.append(f"<h3>What's Inside</h3><p>{shopify.whats_inside}</p>")

        # How to Use
        if shopify.how_to_use:
            sections.append(f"<h3>How to Use</h3><p>{shopify.how_to_use}</p>")

        # Product Story
        if shopify.product_story:
            sections.append(f"<h3>Product Story</h3><p>{shopify.product_story}</p>")

        # Ingredients
        if shopify.ingredients:
            ing_html = "".join(f"<li>{i}</li>" for i in shopify.ingredients)
            sections.append(f"<h3>Ingredients</h3><ol>{ing_html}</ol>")

        # Certifications
        if shopify.certifications:
            cert_html = "".join(f"<li>{c}</li>" for c in shopify.certifications)
            sections.append(f"<h3>Certifications</h3><ol>{cert_html}</ol>")

        # About Brand
        if shopify.about_brand:
            sections.append(f"<h3>About the Brand</h3><p>{shopify.about_brand}</p>")

        # Shipping
        if shopify.shipping:
            sections.append(f"<h3>Shipping</h3><p>{shopify.shipping}</p>")

        return "\n".join(sections)

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text.strip("-")
