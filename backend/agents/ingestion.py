import json
import uuid
from pathlib import Path
import pandas as pd
from backend.agents.base import BaseAgent
from backend.models.product import RawProduct


class IngestionAgent(BaseAgent):
    """Agent 1: Reads raw product data from CSV, JSON, or Excel files."""

    name = "ingestion"

    async def run(self, input_data: str | Path) -> list[RawProduct]:
        """Read a file and return a list of RawProduct objects.

        Args:
            input_data: Path to the uploaded file (CSV, JSON, or Excel).

        Returns:
            List of RawProduct objects.
        """
        file_path = Path(input_data)
        suffix = file_path.suffix.lower()

        if suffix == ".csv":
            df = pd.read_csv(file_path)
        elif suffix in (".xlsx", ".xls"):
            df = pd.read_excel(file_path)
        elif suffix == ".json":
            with open(file_path) as f:
                data = json.load(f)
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame([data])
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Use CSV, JSON, or Excel.")

        # Build a case-insensitive column lookup: lowercase -> original column name
        col_lookup = {}
        for c in df.columns:
            key = str(c).strip().lower().replace(" ", "_")
            col_lookup[key] = c

        products = []
        for idx, row in df.iterrows():
            raw = row.to_dict()

            # Helper to pop a value by lowercase key
            def pop_val(key: str, default="") -> str:
                orig_col = col_lookup.get(key)
                if orig_col is not None and orig_col in raw:
                    val = raw.pop(orig_col)
                    if pd.notna(val):
                        return str(val).strip()
                return default

            # Helper to pop first found from multiple keys
            def pop_first(*keys, default="") -> str:
                for k in keys:
                    v = pop_val(k, default=None)
                    if v is not None and v:
                        return v
                return default

            # Core fields
            product_id = pop_first("id", default="") or uuid.uuid4().hex[:8]
            title = pop_first("title", "product_title", "name", "product_name")
            # Use Body HTML as description if no description column
            description = pop_first("description", "product_description", "body_html")
            brand = pop_first("brand", "vendor", "manufacturer")
            vendor = pop_first("vendor", "seller")

            # Image — only grab Image Src, not Image Type, Image Command, etc.
            images = _extract_image_src(raw, col_lookup)

            # Price — from variant_price or price
            price = pop_first("variant_price", "price")

            # Pass-through fields for Matrixify
            handle = pop_first("handle")
            tags = pop_first("tags")
            variant_sku = pop_first("variant_sku")
            variant_price = price or pop_first("variant_price")
            variant_barcode = pop_first("variant_barcode")
            variant_weight = pop_first("variant_weight")
            variant_weight_unit = pop_first("variant_weight_unit")
            product_type = pop_first("type", "product_type")
            status = pop_first("status")
            published = pop_first("published")
            image_alt_text = pop_first("image_alt_text")

            # Remaining fields go to extra_fields
            extra_fields = {}
            for col_name, val in raw.items():
                if pd.notna(val) and str(val).strip():
                    extra_fields[str(col_name)] = str(val)

            product = RawProduct(
                id=str(product_id),
                title=title,
                description=description,
                brand=brand or vendor,
                images=images,
                price=price or None,
                vendor=vendor or brand,
                handle=handle,
                tags=tags,
                variant_sku=variant_sku,
                variant_price=variant_price,
                variant_barcode=variant_barcode,
                variant_weight=variant_weight,
                variant_weight_unit=variant_weight_unit,
                product_type=product_type,
                status=status,
                published=published,
                image_alt_text=image_alt_text,
                extra_fields=extra_fields,
            )
            products.append(product)

        return products


def _extract_image_src(raw: dict, col_lookup: dict) -> list[str]:
    """Extract only actual image URLs from Image Src column."""
    images = []

    # Only use "image_src" column — the actual image URL column
    orig_col = col_lookup.get("image_src")
    if orig_col and orig_col in raw:
        val = str(raw.pop(orig_col, ""))
        if val and val != "nan":
            for url in val.replace("|", ",").split(","):
                url = url.strip()
                if url and url.startswith("http"):
                    images.append(url)

    # Also check variant_image for additional images
    orig_col = col_lookup.get("variant_image")
    if orig_col and orig_col in raw:
        val = str(raw.pop(orig_col, ""))
        if val and val != "nan":
            for url in val.replace("|", ",").split(","):
                url = url.strip()
                if url and url.startswith("http"):
                    images.append(url)

    return images
