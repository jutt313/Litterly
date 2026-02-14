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


# ─── Agent 6 Output: Export Row ───

class ExportRow(BaseModel):
    handle: str = ""
    title: str = ""
    body_html: str = ""
    vendor: str = ""
    product_type: str = ""
    tags: str = ""
    variant_sku: str = ""
    variant_weight: str = ""
    variant_weight_unit: str = "g"
    image_src: str = ""
    image_alt_text: str = ""
    seo_title: str = ""
    seo_description: str = ""
    # Metafields for custom sections
    metafield_usps: str = ""
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
