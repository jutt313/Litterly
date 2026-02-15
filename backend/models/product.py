from pydantic import BaseModel, Field


# ─── Agent 1 Output: Raw Product ───

class RawProduct(BaseModel):
    id: str
    title: str = ""
    description: str = ""
    brand: str = ""
    images: list[str] = Field(default_factory=list)
    price: str | None = None
    vendor: str | None = None
    # Preserved from input for pass-through
    handle: str = ""
    tags: str = ""
    variant_sku: str = ""
    variant_price: str = ""
    variant_barcode: str = ""
    variant_weight: str = ""
    variant_weight_unit: str = ""
    product_type: str = ""
    status: str = ""
    published: str = ""
    image_alt_text: str = ""
    extra_fields: dict = Field(default_factory=dict)


# ─── Agent 2 Output: Matched Product ───

class MatchResult(BaseModel):
    source: str  # "amazon_japan", "rakuten", "vendor_site", etc.
    url: str
    title: str = ""
    confidence: float = 0.0  # 0-1
    match_reason: str = ""

class MatchedProduct(BaseModel):
    raw: RawProduct
    matches: list[MatchResult] = Field(default_factory=list)


# ─── Agent 3 Output: Extracted Product ───

class SourceData(BaseModel):
    source: str
    url: str
    title: str = ""
    description: str = ""
    price: str | None = None
    weight: str | None = None
    dimensions: str | None = None
    images: list[str] = Field(default_factory=list)
    specs: dict = Field(default_factory=dict)
    reviews_summary: str | None = None
    ingredients: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    rating: str | None = None
    review_count: str | None = None

class ExtractedProduct(BaseModel):
    raw: RawProduct
    matches: list[MatchResult] = Field(default_factory=list)
    sources: list[SourceData] = Field(default_factory=list)


# ─── Agent 4 Output: Merged Product ───

class ProductVariant(BaseModel):
    name: str
    specs: dict = Field(default_factory=dict)

class MergedProduct(BaseModel):
    raw: RawProduct
    merged_title: str = ""
    merged_description: str = ""
    brand: str = ""
    all_images: list[str] = Field(default_factory=list)
    price_range: str | None = None
    weight: str | None = None
    dimensions: str | None = None
    ingredients: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    reviews_summary: str = ""
    variants: list[ProductVariant] = Field(default_factory=list)
    all_specs: dict = Field(default_factory=dict)
    sources_used: list[str] = Field(default_factory=list)
    rating: str | None = None
    review_count: str | None = None
    monthly_sales: str | None = None


# ─── Agent 5 Output: Shopify Product ───

class ShopifyProduct(BaseModel):
    title: str = ""                     # Section 1: Max 7 words
    description: str = ""               # Section 2: Max 4 sentences, 30 words
    usps: list[str] = Field(default_factory=list)  # Section 3: 6 USPs, max 3 words each
    specifications: str = ""            # Section 4: Rich text format
    who_is_this_for: list[str] = Field(default_factory=list)  # Section 5: 5 avatars
    benefits: list[str] = Field(default_factory=list)  # Section 6: 8+ benefits
    features: list[str] = Field(default_factory=list)  # Section 7: 10+ features
    whats_inside: str = ""              # Section 8
    how_to_use: str = ""                # Section 9
    product_story: str = ""             # Section 10: Max 200 words, 1 paragraph
    ingredients: list[str] = Field(default_factory=list)  # Section 11
    certifications: list[str] = Field(default_factory=list)  # Section 12
    about_brand: str = ""               # Section 13: 1 paragraph
    shipping: str = ""                  # Section 14
    sold_in_stores: list[str] = Field(default_factory=list)  # Section 15


# ─── Agent 6 Output: Export Row (Matrixify-compatible) ───

class ExportRow(BaseModel):
    """Matrixify-compatible export row with exact Shopify column names."""
    # Core Shopify fields
    handle: str = ""
    command: str = "UPDATE"
    title: str = ""
    body_html: str = ""
    vendor: str = ""
    product_type: str = ""
    tags: str = ""
    status: str = "Active"
    published: str = "TRUE"
    image_src: str = ""
    image_alt_text: str = ""
    # Variant fields
    variant_sku: str = ""
    variant_price: str = ""
    variant_barcode: str = ""
    variant_weight: str = ""
    variant_weight_unit: str = "g"
    # SEO
    seo_title: str = ""
    seo_description: str = ""
    # Metafields — 6 separate USPs (rich_text_field JSON)
    metafield_usp1: str = ""
    metafield_usp2: str = ""
    metafield_usp3: str = ""
    metafield_usp4: str = ""
    metafield_usp5: str = ""
    metafield_usp6: str = ""
    # Metafields — other sections (rich_text_field JSON)
    metafield_specifications: str = ""
    metafield_who_is_this_for: str = ""
    metafield_benefits: str = ""
    metafield_features: str = ""
    metafield_whats_inside: str = ""
    metafield_how_to_use: str = ""
    metafield_product_story: str = ""
    metafield_ingredients: str = ""
    metafield_certifications: str = ""
    metafield_about_brand: str = ""
    metafield_shipping: str = ""
    metafield_sold_in_stores: str = ""

    # Mapping from model field names to Matrixify CSV column names
    @staticmethod
    def csv_column_names() -> dict[str, str]:
        return {
            "handle": "Handle",
            "command": "Command",
            "title": "Title",
            "body_html": "Body HTML",
            "vendor": "Vendor",
            "product_type": "Type",
            "tags": "Tags",
            "status": "Status",
            "published": "Published",
            "image_src": "Image Src",
            "image_alt_text": "Image Alt Text",
            "variant_sku": "Variant SKU",
            "variant_price": "Variant Price",
            "variant_barcode": "Variant Barcode",
            "variant_weight": "Variant Weight",
            "variant_weight_unit": "Variant Weight Unit",
            "seo_title": "Metafield: title_tag [string]",
            "seo_description": "Metafield: description_tag [string]",
            "metafield_usp1": "Metafield: custom.usp1 [rich_text_field]",
            "metafield_usp2": "Metafield: custom.usp2 [rich_text_field]",
            "metafield_usp3": "Metafield: custom.usp3 [rich_text_field]",
            "metafield_usp4": "Metafield: custom.usp4 [rich_text_field]",
            "metafield_usp5": "Metafield: custom.usp5 [rich_text_field]",
            "metafield_usp6": "Metafield: custom.usp6 [rich_text_field]",
            "metafield_specifications": "Metafield: custom.specifications_new [rich_text_field]",
            "metafield_who_is_this_for": "Metafield: custom.who_is_this_for_new [rich_text_field]",
            "metafield_benefits": "Metafield: custom.product_benefits_new [rich_text_field]",
            "metafield_features": "Metafield: custom.features_new [rich_text_field]",
            "metafield_whats_inside": "Metafield: custom.what_s_inside_new [rich_text_field]",
            "metafield_how_to_use": "Metafield: custom.how_to_use_new [rich_text_field]",
            "metafield_product_story": "Metafield: custom.product_story_new [rich_text_field]",
            "metafield_ingredients": "Metafield: custom.ingredients_new [rich_text_field]",
            "metafield_certifications": "Metafield: custom.certifications_new [rich_text_field]",
            "metafield_about_brand": "Metafield: custom.about_brand_new [rich_text_field]",
            "metafield_shipping": "Metafield: custom.shipping [rich_text_field]",
            "metafield_sold_in_stores": "Metafield: custom.as_sold_in_new [rich_text_field]",
        }

    def to_csv_dict(self) -> dict[str, str]:
        """Convert to dict with Matrixify-compatible column names."""
        data = self.model_dump()
        col_map = self.csv_column_names()
        return {col_map.get(k, k): v for k, v in data.items()}
