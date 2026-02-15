import time
import logging
from backend.llm import get_llm
from backend.llm.base import BaseLLM
from backend.models.product import RawProduct, ShopifyProduct, ExportRow
from backend.models.pipeline import ProductStatus
from backend.agents.matcher import MatcherAgent
from backend.agents.extractor import ExtractorAgent
from backend.agents.merger import MergerAgent
from backend.agents.copywriter import CopywriterAgent
from backend.agents.exporter import ExporterAgent

logger = logging.getLogger("litterly.pipeline")


class PipelineRunner:
    """Runs a single product through all 6 agents sequentially."""

    def __init__(self, llm_provider: str = "deepseek"):
        logger.info(f"[PIPELINE] Initializing pipeline with LLM provider: {llm_provider}")
        self.llm: BaseLLM = get_llm(llm_provider)
        self.llm_provider = llm_provider

        # Initialize agents
        self.matcher = MatcherAgent(llm=self.llm)
        self.extractor = ExtractorAgent(llm=self.llm)
        self.merger = MergerAgent(llm=self.llm)
        self.copywriter = CopywriterAgent(llm=self.llm)
        self.exporter = ExporterAgent()
        logger.info(f"[PIPELINE] All 6 agents initialized")

    async def run_product(
        self,
        product: RawProduct,
        on_status_change=None,
    ) -> ExportRow:
        """Run a single product through the full pipeline."""
        product_id = product.id
        pipeline_start = time.time()

        logger.info(f"{'='*60}")
        logger.info(f"[{product_id}] PIPELINE START")
        logger.info(f"[{product_id}]   Title: {product.title}")
        logger.info(f"[{product_id}]   Brand: {product.brand}")
        logger.info(f"[{product_id}]   Description: {product.description[:100]}..." if len(product.description) > 100 else f"[{product_id}]   Description: {product.description}")
        logger.info(f"[{product_id}]   Images: {len(product.images)}")
        logger.info(f"[{product_id}]   Price: {product.price}")
        logger.info(f"[{product_id}]   Extra fields: {list(product.extra_fields.keys())}")
        logger.info(f"[{product_id}]   LLM: {self.llm_provider}")
        logger.info(f"{'='*60}")

        async def update_status(status: ProductStatus):
            if on_status_change:
                await on_status_change(product_id, status)

        try:
            # ─── Agent 2: Match product online ───
            await update_status(ProductStatus.MATCHING)
            agent_start = time.time()
            logger.info(f"[{product_id}] [AGENT 2: MATCHER] Starting...")
            logger.info(f"[{product_id}] [MATCHER] Searching DuckDuckGo for: '{product.brand} {product.title}'")
            logger.info(f"[{product_id}] [MATCHER] Target sites: amazon.co.jp, rakuten.co.jp + general search")

            matched = await self.matcher.run(product)

            agent_time = round(time.time() - agent_start, 1)
            logger.info(f"[{product_id}] [MATCHER] Found {len(matched.matches)} matches in {agent_time}s")
            for i, m in enumerate(matched.matches):
                logger.info(f"[{product_id}] [MATCHER]   Match {i+1}: {m.source} — confidence: {m.confidence} — {m.url}")
                logger.info(f"[{product_id}] [MATCHER]     Reason: {m.match_reason}")

            if not matched.matches:
                logger.warning(f"[{product_id}] [MATCHER] No matches found! Pipeline will continue with limited data.")

            # ─── Agent 3: Extract data from matched pages ───
            await update_status(ProductStatus.EXTRACTING)
            agent_start = time.time()
            logger.info(f"[{product_id}] [AGENT 3: EXTRACTOR] Starting...")
            logger.info(f"[{product_id}] [EXTRACTOR] Scraping {len(matched.matches)} matched pages...")

            extracted = await self.extractor.run(matched)

            agent_time = round(time.time() - agent_start, 1)
            logger.info(f"[{product_id}] [EXTRACTOR] Extracted data from {len(extracted.sources)} sources in {agent_time}s")
            for i, s in enumerate(extracted.sources):
                logger.info(f"[{product_id}] [EXTRACTOR]   Source {i+1}: {s.source}")
                logger.info(f"[{product_id}] [EXTRACTOR]     Title: {s.title[:80]}")
                logger.info(f"[{product_id}] [EXTRACTOR]     Price: {s.price}")
                logger.info(f"[{product_id}] [EXTRACTOR]     Images: {len(s.images)}")
                logger.info(f"[{product_id}] [EXTRACTOR]     Specs: {len(s.specs)} fields")
                logger.info(f"[{product_id}] [EXTRACTOR]     Ingredients: {len(s.ingredients)}")
                logger.info(f"[{product_id}] [EXTRACTOR]     Certifications: {len(s.certifications)}")
                logger.info(f"[{product_id}] [EXTRACTOR]     Rating: {s.rating}, Reviews: {s.review_count}")

            # ─── Agent 4: Merge all data ───
            await update_status(ProductStatus.MERGING)
            agent_start = time.time()
            logger.info(f"[{product_id}] [AGENT 4: MERGER] Starting...")
            logger.info(f"[{product_id}] [MERGER] Merging data from {len(extracted.sources)} sources + original scraped data")

            merged = await self.merger.run(extracted)

            agent_time = round(time.time() - agent_start, 1)
            logger.info(f"[{product_id}] [MERGER] Merge complete in {agent_time}s")
            logger.info(f"[{product_id}] [MERGER]   Merged title: {merged.merged_title}")
            logger.info(f"[{product_id}] [MERGER]   Brand: {merged.brand}")
            logger.info(f"[{product_id}] [MERGER]   Total images: {len(merged.all_images)}")
            logger.info(f"[{product_id}] [MERGER]   Ingredients: {len(merged.ingredients)}")
            logger.info(f"[{product_id}] [MERGER]   Certifications: {len(merged.certifications)}")
            logger.info(f"[{product_id}] [MERGER]   Variants: {len(merged.variants)}")
            logger.info(f"[{product_id}] [MERGER]   Specs: {len(merged.all_specs)} fields")
            logger.info(f"[{product_id}] [MERGER]   Sources used: {merged.sources_used}")
            logger.info(f"[{product_id}] [MERGER]   Rating: {merged.rating}, Reviews: {merged.review_count}")

            # ─── Agent 5: Generate copywriting ───
            await update_status(ProductStatus.COPYWRITING)
            agent_start = time.time()
            logger.info(f"[{product_id}] [AGENT 5: COPYWRITER] Starting...")
            logger.info(f"[{product_id}] [COPYWRITER] Generating all 15 Shopify sections...")
            logger.info(f"[{product_id}] [COPYWRITER] Using copywriting prompt with psychological framework")

            shopify_product = await self.copywriter.run(merged)

            agent_time = round(time.time() - agent_start, 1)
            logger.info(f"[{product_id}] [COPYWRITER] Copy generated in {agent_time}s")
            logger.info(f"[{product_id}] [COPYWRITER]   1. Title: {shopify_product.title}")
            logger.info(f"[{product_id}] [COPYWRITER]   2. Description: {shopify_product.description[:80]}...")
            logger.info(f"[{product_id}] [COPYWRITER]   3. USPs: {len(shopify_product.usps)} items")
            logger.info(f"[{product_id}] [COPYWRITER]   4. Specifications: {'yes' if shopify_product.specifications else 'empty'}")
            logger.info(f"[{product_id}] [COPYWRITER]   5. Who is this for: {len(shopify_product.who_is_this_for)} avatars")
            logger.info(f"[{product_id}] [COPYWRITER]   6. Benefits: {len(shopify_product.benefits)} items")
            logger.info(f"[{product_id}] [COPYWRITER]   7. Features: {len(shopify_product.features)} items")
            logger.info(f"[{product_id}] [COPYWRITER]   8. What's inside: {'yes' if shopify_product.whats_inside else 'empty'}")
            logger.info(f"[{product_id}] [COPYWRITER]   9. How to use: {'yes' if shopify_product.how_to_use else 'empty'}")
            logger.info(f"[{product_id}] [COPYWRITER]  10. Product story: {'yes' if shopify_product.product_story else 'empty'}")
            logger.info(f"[{product_id}] [COPYWRITER]  11. Ingredients: {len(shopify_product.ingredients)} items")
            logger.info(f"[{product_id}] [COPYWRITER]  12. Certifications: {len(shopify_product.certifications)} items")
            logger.info(f"[{product_id}] [COPYWRITER]  13. About brand: {'yes' if shopify_product.about_brand else 'empty'}")
            logger.info(f"[{product_id}] [COPYWRITER]  14. Shipping: {'yes' if shopify_product.shipping else 'empty'}")
            logger.info(f"[{product_id}] [COPYWRITER]  15. Sold in stores: {len(shopify_product.sold_in_stores)} items")

            # ─── Agent 6: Export to Matrixify format ───
            await update_status(ProductStatus.EXPORTING)
            agent_start = time.time()
            logger.info(f"[{product_id}] [AGENT 6: EXPORTER] Starting...")
            logger.info(f"[{product_id}] [EXPORTER] Mapping 15 sections to Matrixify CSV columns")

            export_row = await self.exporter.run((merged, shopify_product))

            agent_time = round(time.time() - agent_start, 1)
            logger.info(f"[{product_id}] [EXPORTER] Export complete in {agent_time}s")
            logger.info(f"[{product_id}] [EXPORTER]   Handle: {export_row.handle}")
            logger.info(f"[{product_id}] [EXPORTER]   Title: {export_row.title}")
            logger.info(f"[{product_id}] [EXPORTER]   Body HTML: {len(export_row.body_html)} chars")
            logger.info(f"[{product_id}] [EXPORTER]   Image: {export_row.image_src[:80] if export_row.image_src else 'none'}")

            # ─── Done ───
            await update_status(ProductStatus.COMPLETED)
            total_time = round(time.time() - pipeline_start, 1)

            logger.info(f"{'='*60}")
            logger.info(f"[{product_id}] PIPELINE COMPLETE — {total_time}s total")
            logger.info(f"[{product_id}]   Matches found: {len(matched.matches)}")
            logger.info(f"[{product_id}]   Sources scraped: {len(extracted.sources)}")
            logger.info(f"[{product_id}]   Sections generated: 15")
            logger.info(f"[{product_id}]   Output title: {shopify_product.title}")
            logger.info(f"{'='*60}")

            return export_row

        except Exception as e:
            await update_status(ProductStatus.ERROR)
            total_time = round(time.time() - pipeline_start, 1)
            logger.error(f"{'='*60}")
            logger.error(f"[{product_id}] PIPELINE FAILED after {total_time}s")
            logger.error(f"[{product_id}]   Error: {type(e).__name__}: {e}")
            logger.error(f"{'='*60}")
            raise
