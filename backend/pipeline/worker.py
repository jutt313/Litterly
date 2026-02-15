import asyncio
import csv
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from backend.config import settings
from backend.models.product import RawProduct, ExportRow
from backend.models.pipeline import Job, JobStatus, ProductProgress, ProductStatus
from backend.pipeline.runner import PipelineRunner

logger = logging.getLogger("litterly.worker")

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


class WorkerManager:
    """Manages parallel workers processing products through the pipeline."""

    def __init__(self, job: Job):
        self.job = job
        self.queue: asyncio.Queue[RawProduct] = asyncio.Queue()
        self.results: list[ExportRow] = []
        self.lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
        self._csv_header_written = False

        # Create job folder
        self.job_folder = self._create_job_folder()
        self.job.job_folder = str(self.job_folder)
        self.live_csv_path = self.job_folder / "matrixify_live.csv"
        self.final_csv_path = self.job_folder / "matrixify_final.csv"

    def _create_job_folder(self) -> Path:
        """Create a folder for this job using the job name."""
        # Clean filename for folder name
        safe_name = re.sub(r'[^\w\s-]', '', Path(self.job.filename).stem)
        safe_name = re.sub(r'[\s]+', '_', safe_name).strip('_')
        folder_name = f"{self.job.id}_{safe_name}"

        job_folder = settings.OUTPUT_DIR / folder_name
        job_folder.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created job folder: {job_folder}")
        return job_folder

    async def start(self, products: list[RawProduct]):
        """Start processing products with parallel workers."""
        self.job.status = JobStatus.RUNNING
        self.job.started_at = datetime.now()
        self.job.total_products = len(products)
        self._save_job()

        # Fill the queue
        for p in products:
            await self.queue.put(p)

        # Create workers
        num_workers = min(self.job.workers, len(products))
        logger.info(f"Starting {num_workers} workers for {len(products)} products")

        workers = [
            asyncio.create_task(self._worker(i))
            for i in range(num_workers)
        ]

        # Wait for all products to be processed
        await self.queue.join()

        # Cancel workers
        for w in workers:
            w.cancel()

        # Write final CSV (complete copy)
        if self.results:
            await self._export_final_csv()

        self.job.output_file = str(self.final_csv_path)
        self.job.status = JobStatus.COMPLETED
        self.job.completed_at = datetime.now()
        self._save_job()

        logger.info(f"Job {self.job.id} completed: {self.job.completed_products}/{self.job.total_products} products")

    async def stop(self):
        """Stop all workers."""
        self._stop_event.set()
        self.job.status = JobStatus.PAUSED
        self._save_job()

    async def _worker(self, worker_id: int):
        """Single worker that processes products from the queue."""
        runner = PipelineRunner(llm_provider=self.job.llm_provider)

        while not self._stop_event.is_set():
            try:
                product = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            try:
                # Process with retries
                export_row = await self._process_with_retry(runner, product, worker_id)

                async with self.lock:
                    self.results.append(export_row)
                    self.job.completed_products += 1
                    self._update_product_status(product.id, ProductStatus.COMPLETED)

                    # Write to live CSV immediately
                    self._append_to_live_csv(export_row)

                    self._save_job()

            except Exception as e:
                logger.error(f"Worker {worker_id}: Product {product.id} failed after retries: {e}")
                async with self.lock:
                    self.job.failed_products += 1
                    self._update_product_status(product.id, ProductStatus.ERROR, str(e))
                    self._save_job()

            finally:
                self.queue.task_done()

    async def _process_with_retry(
        self, runner: PipelineRunner, product: RawProduct, worker_id: int
    ) -> ExportRow:
        """Process a product with auto-retry on failure."""
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"Worker {worker_id}: Processing {product.id} (attempt {attempt})")

                async def on_status_change(product_id: str, status: ProductStatus):
                    async with self.lock:
                        self._update_product_status(product_id, status)
                        self._save_job()

                return await runner.run_product(product, on_status_change=on_status_change)

            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY * attempt
                    logger.warning(f"Worker {worker_id}: Product {product.id} failed (attempt {attempt}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)

        raise last_error

    def _update_product_status(self, product_id: str, status: ProductStatus, error: str | None = None):
        """Update a product's status in the job."""
        for p in self.job.products:
            if p.product_id == product_id:
                p.status = status
                p.current_agent = status.value
                if error:
                    p.error = error
                if status == ProductStatus.COMPLETED:
                    p.completed_at = datetime.now()
                elif p.started_at is None:
                    p.started_at = datetime.now()
                break

    def _append_to_live_csv(self, row: ExportRow):
        """Append a single product row to the live CSV file (updates in real-time)."""
        csv_row = row.to_csv_dict()
        fieldnames = list(csv_row.keys())

        # Write header if first row
        if not self._csv_header_written:
            with open(self.live_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(csv_row)
            self._csv_header_written = True
        else:
            with open(self.live_csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow(csv_row)

        logger.info(f"Live CSV updated: {self.live_csv_path} ({len(self.results)} products)")

    async def _export_final_csv(self):
        """Export all results to a final Matrixify-compatible CSV."""
        if not self.results:
            return

        fieldnames = list(self.results[0].to_csv_dict().keys())

        with open(self.final_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.results:
                writer.writerow(row.to_csv_dict())

        logger.info(f"Final CSV exported: {self.final_csv_path} ({len(self.results)} products)")

    def _save_job(self):
        """Save job state to disk for persistence."""
        # Save to main jobs dir (for tracking)
        job_path = settings.JOBS_DIR / f"{self.job.id}.json"
        with open(job_path, "w") as f:
            f.write(self.job.model_dump_json(indent=2))

        # Also save a copy in the job folder
        job_folder_path = self.job_folder / "job.json"
        with open(job_folder_path, "w") as f:
            f.write(self.job.model_dump_json(indent=2))
