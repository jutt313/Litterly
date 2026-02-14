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

        # Clean column names
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

        products = []
        for idx, row in df.iterrows():
            row_dict = row.to_dict()

            # Map common column names to RawProduct fields
            product = RawProduct(
                id=str(row_dict.pop("id", "") or uuid.uuid4().hex[:8]),
                title=str(row_dict.pop("title", "") or row_dict.pop("product_title", "") or row_dict.pop("name", "") or row_dict.pop("product_name", "") or ""),
                description=str(row_dict.pop("description", "") or row_dict.pop("product_description", "") or ""),
                brand=str(row_dict.pop("brand", "") or row_dict.pop("vendor", "") or row_dict.pop("manufacturer", "") or ""),
                images=_extract_images(row_dict),
                price=str(row_dict.pop("price", "") or "") or None,
                vendor=str(row_dict.pop("vendor", "") or row_dict.pop("seller", "") or "") or None,
                extra_fields={k: str(v) for k, v in row_dict.items() if pd.notna(v) and str(v).strip()},
            )
            products.append(product)

        return products


def _extract_images(row_dict: dict) -> list[str]:
    """Extract image URLs from row data."""
    images = []

    # Check for image columns
    for key in list(row_dict.keys()):
        if "image" in key or "img" in key or "photo" in key:
            val = str(row_dict.pop(key, ""))
            if val and val != "nan":
                # Could be comma-separated or pipe-separated
                for url in val.replace("|", ",").split(","):
                    url = url.strip()
                    if url:
                        images.append(url)

    return images
