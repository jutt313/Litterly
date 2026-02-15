import json
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
        raw = merged.raw

        # Build body HTML from all sections
        body_html = self._build_body_html(shopify)

        # Use original handle if available, otherwise generate from title
        handle = raw.handle if raw.handle else self._slugify(shopify.title)

        # Use original image if available, otherwise use first from merged
        image_src = ""
        if raw.images:
            image_src = raw.images[0]
        elif merged.all_images:
            # Filter out non-URL entries
            for img in merged.all_images:
                if img.startswith("http"):
                    image_src = img
                    break

        # Build 6 separate USPs in rich_text_field JSON
        usps_padded = (shopify.usps + [""] * 6)[:6]

        return ExportRow(
            # Core fields — preserve from input where available
            handle=handle,
            command="UPDATE",
            title=shopify.title,
            body_html=body_html,
            vendor=merged.brand or raw.vendor or "",
            product_type=raw.product_type,
            tags=raw.tags,
            status=raw.status or "Active",
            published=raw.published or "TRUE",
            image_src=image_src,
            image_alt_text=raw.image_alt_text or shopify.title,
            # Variant fields — preserve from input
            variant_sku=raw.variant_sku,
            variant_price=raw.variant_price or raw.price or "",
            variant_barcode=raw.variant_barcode,
            variant_weight=raw.variant_weight or merged.weight or "",
            variant_weight_unit=raw.variant_weight_unit or "g",
            # SEO
            seo_title=shopify.title,
            seo_description=shopify.description,
            # 6 separate USP metafields
            metafield_usp1=_to_rich_text(usps_padded[0]),
            metafield_usp2=_to_rich_text(usps_padded[1]),
            metafield_usp3=_to_rich_text(usps_padded[2]),
            metafield_usp4=_to_rich_text(usps_padded[3]),
            metafield_usp5=_to_rich_text(usps_padded[4]),
            metafield_usp6=_to_rich_text(usps_padded[5]),
            # Other metafields in rich_text_field JSON
            metafield_specifications=_to_rich_text(shopify.specifications),
            metafield_who_is_this_for=_to_rich_text("\n".join(shopify.who_is_this_for)),
            metafield_benefits=_to_rich_text("\n".join(shopify.benefits)),
            metafield_features=_to_rich_text("\n".join(shopify.features)),
            metafield_whats_inside=_to_rich_text(shopify.whats_inside),
            metafield_how_to_use=_to_rich_text(shopify.how_to_use),
            metafield_product_story=_to_rich_text(shopify.product_story),
            metafield_ingredients=_to_rich_text("\n".join(shopify.ingredients)),
            metafield_certifications=_to_rich_text("\n".join(shopify.certifications)),
            metafield_about_brand=_to_rich_text(shopify.about_brand),
            metafield_shipping=_to_rich_text(shopify.shipping),
            metafield_sold_in_stores=_to_rich_text("\n".join(shopify.sold_in_stores)),
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


def _to_rich_text(text: str) -> str:
    """Convert plain text to Shopify rich_text_field JSON format.

    Shopify metafields of type rich_text_field expect JSON in this format:
    {"type": "root", "children": [{"type": "paragraph", "children": [{"type": "text", "value": "..."}]}]}
    """
    if not text or not text.strip():
        return ""

    return json.dumps({
        "type": "root",
        "children": [
            {
                "type": "paragraph",
                "children": [
                    {"type": "text", "value": text.strip()}
                ]
            }
        ]
    })
