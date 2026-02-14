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
        self.llm: BaseLLM = get_llm(llm_provider)

        # Initialize agents
        self.matcher = MatcherAgent(llm=self.llm)
        self.extractor = ExtractorAgent(llm=self.llm)
        self.merger = MergerAgent(llm=self.llm)
        self.copywriter = CopywriterAgent(llm=self.llm)
        self.exporter = ExporterAgent()

    async def run_product(
        self,
        product: RawProduct,
        on_status_change=None,
    ) -> ExportRow:
        """Run a single product through the full pipeline.

        Args:
            product: RawProduct to process.
            on_status_change: Optional callback(product_id, status) for progress updates.

        Returns:
            ExportRow ready for CSV export.
        """
        product_id = product.id

        async def update_status(status: ProductStatus):
            if on_status_change:
                await on_status_change(product_id, status)

        try:
            # Agent 2: Match product online
            await update_status(ProductStatus.MATCHING)
            logger.info(f"[{product_id}] Matching product: {product.title}")
            matched = await self.matcher.run(product)
            logger.info(f"[{product_id}] Found {len(matched.matches)} matches")

            # Agent 3: Extract data from matched pages
            await update_status(ProductStatus.EXTRACTING)
            logger.info(f"[{product_id}] Extracting data from matched pages")
            extracted = await self.extractor.run(matched)
            logger.info(f"[{product_id}] Extracted from {len(extracted.sources)} sources")

            # Agent 4: Merge all data
            await update_status(ProductStatus.MERGING)
            logger.info(f"[{product_id}] Merging data from all sources")
            merged = await self.merger.run(extracted)

            # Agent 5: Generate copywriting
            await update_status(ProductStatus.COPYWRITING)
            logger.info(f"[{product_id}] Generating Shopify copy (15 sections)")
            shopify_product = await self.copywriter.run(merged)

            # Agent 6: Export to Matrixify format
            await update_status(ProductStatus.EXPORTING)
            logger.info(f"[{product_id}] Formatting for Matrixify export")
            export_row = await self.exporter.run((merged, shopify_product))

            await update_status(ProductStatus.COMPLETED)
            logger.info(f"[{product_id}] Completed successfully")

            return export_row

        except Exception as e:
            await update_status(ProductStatus.ERROR)
            logger.error(f"[{product_id}] Pipeline failed: {e}")
            raise
