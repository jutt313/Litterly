import csv
import logging
from pathlib import Path
from backend.agents.base import BaseAgent
from backend.models.pipeline import Job, ProductStatus
from backend.config import settings

logger = logging.getLogger("litterly.chat")


class ChatAgent(BaseAgent):
    """Chat agent that helps users understand job status, diagnose errors,
    and interact with product data."""

    name = "chat"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        prompt_path = settings.PROMPTS_DIR / "chat.txt"
        if prompt_path.exists():
            self.system_prompt = prompt_path.read_text(encoding="utf-8")
        else:
            self.system_prompt = "You are Litterly, a helpful AI assistant for a product enrichment pipeline. Be concise and practical."

    async def run(self, input_data: dict) -> str:
        """Process a chat message with job context.

        Args:
            input_data: Dict with message, job_id, conversation_history.

        Returns:
            Litterly's response string.
        """
        message = input_data["message"]
        job_id = input_data["job_id"]
        history = input_data.get("conversation_history", [])

        # Build context from job data
        context = self._build_context(job_id)

        # Build full prompt
        prompt = self._build_prompt(message, context, history)

        logger.info(f"[CHAT] Job {job_id} — User: {message[:80]}")

        response = await self.llm.generate(prompt, system_prompt=self.system_prompt)

        logger.info(f"[CHAT] Job {job_id} — Response: {len(response)} chars")
        return response

    def _build_context(self, job_id: str) -> dict:
        """Build comprehensive context from job data."""
        job = self._load_job(job_id)

        # Product lists by status
        completed = []
        failed = []
        active = []
        pending = []

        for p in job.products:
            info = {"id": p.product_id, "title": p.title}
            if p.status == ProductStatus.COMPLETED:
                completed.append(info)
            elif p.status == ProductStatus.ERROR:
                failed.append({**info, "error": p.error or "Unknown error", "agent": p.current_agent})
            elif p.status == ProductStatus.PENDING:
                pending.append(info)
            else:
                active.append({**info, "agent": p.current_agent})

        # CSV preview
        csv_preview = self._get_csv_preview(job)

        return {
            "job_id": job.id,
            "filename": job.filename,
            "status": job.status.value,
            "total": job.total_products,
            "completed_count": job.completed_products,
            "failed_count": job.failed_products,
            "llm_provider": job.llm_provider,
            "workers": job.workers,
            "job_folder": job.job_folder,
            "output_file": job.output_file,
            "completed": completed,
            "failed": failed,
            "active": active,
            "pending": pending,
            "csv_preview": csv_preview,
        }

    def _load_job(self, job_id: str) -> Job:
        job_path = settings.JOBS_DIR / f"{job_id}.json"
        if not job_path.exists():
            raise ValueError(f"Job {job_id} not found")
        with open(job_path) as f:
            return Job.model_validate_json(f.read())

    def _get_csv_preview(self, job: Job) -> str:
        """Get a preview of CSV output (first 5 rows, key fields)."""
        if not job.job_folder:
            return "No output yet — job hasn't started."

        # Try live CSV, then final
        csv_path = Path(job.job_folder) / "matrixify_live.csv"
        if not csv_path.exists():
            csv_path = Path(job.job_folder) / "matrixify_final.csv"
        if not csv_path.exists():
            return "No CSV output yet — no products completed."

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = []
                for i, row in enumerate(reader):
                    if i >= 5:
                        break
                    rows.append({
                        "title": row.get("Title", row.get("title", "")),
                        "vendor": row.get("Vendor", row.get("vendor", "")),
                        "handle": row.get("Handle", row.get("handle", "")),
                        "image": "yes" if row.get("Image Src", row.get("image_src", "")) else "no",
                        "body_html_len": len(row.get("Body HTML", row.get("body_html", ""))),
                    })

            total_in_csv = sum(1 for _ in open(csv_path, encoding="utf-8")) - 1
            lines = [f"CSV has {total_in_csv} products. Preview (first {len(rows)}):"]
            for r in rows:
                lines.append(f"  - {r['title']} | vendor: {r['vendor']} | image: {r['image']} | body: {r['body_html_len']} chars")
            return "\n".join(lines)
        except Exception as e:
            return f"Error reading CSV: {e}"

    def _build_prompt(self, message: str, context: dict, history: list[dict]) -> str:
        """Build the full prompt with context and conversation history."""
        # Conversation history (last 6 messages)
        history_text = ""
        if history:
            recent = history[-6:]
            history_text = "CONVERSATION HISTORY:\n"
            for msg in recent:
                role = "User" if msg.get("role") == "user" else "Litterly"
                history_text += f"{role}: {msg.get('content', '')}\n"
            history_text += "\n"

        # Errors
        errors_text = ""
        if context["failed"]:
            errors_text = f"\nFAILED PRODUCTS ({len(context['failed'])}):\n"
            for err in context["failed"][:10]:
                errors_text += f"  - {err['title']} — failed at {err['agent']}: {err['error']}\n"

        # Active
        active_text = ""
        if context["active"]:
            active_text = f"\nCURRENTLY PROCESSING ({len(context['active'])}):\n"
            for p in context["active"][:5]:
                active_text += f"  - {p['title']} (stage: {p['agent']})\n"

        # Pending
        pending_text = ""
        if context["pending"]:
            pending_text = f"\nPENDING: {len(context['pending'])} products waiting\n"

        prompt = f"""JOB CONTEXT:
File: {context['filename']}
Job ID: {context['job_id']}
Status: {context['status']}
Progress: {context['completed_count']}/{context['total']} completed, {context['failed_count']} failed
LLM: {context['llm_provider']} | Workers: {context['workers']}
Job folder: {context['job_folder'] or 'not created yet'}
{errors_text}{active_text}{pending_text}
CSV OUTPUT:
{context['csv_preview']}

{history_text}USER MESSAGE:
{message}"""

        return prompt
