import json
import time
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self):
        self.client = None
        if not settings.GEMINI_API_KEY:
            logger.warning(
                "GEMINI_API_KEY is not set. LLM calls will be skipped and "
                "marked as llm_failed=True."
            )
            return
        try:
            from google import genai
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            self._genai = genai
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")

    def classify_transactions_batch(
        self, transactions: List[Dict[str, Any]], max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Batch-classify transactions via LLM.
        Returns each item with llm_category, llm_raw_response, and llm_failed fields.
        """
        if not self.client or not transactions:
            for t in transactions:
                t["llm_category"] = None
                t["llm_raw_response"] = None
                t["llm_failed"] = True
            return transactions

        prompt = (
            "You are a financial transaction classification AI.\n"
            "Assign exactly one category to each transaction from this list: "
            "Food, Shopping, Travel, Transport, Utilities, Cash Withdrawal, Entertainment, Other.\n"
            "Return the output strictly as a JSON array of objects with keys 'txn_id' and 'category'.\n"
            f"Transactions:\n{json.dumps(transactions)}\n"
        )

        last_raw: Optional[str] = None
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config=self._genai.types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
                last_raw = response.text
                result = json.loads(last_raw)
                result_map = {
                    item["txn_id"]: item.get("category", "Other")
                    for item in result
                    if "txn_id" in item
                }

                for t in transactions:
                    t["llm_category"] = result_map.get(t["txn_id"], "Other")
                    t["llm_raw_response"] = last_raw
                    t["llm_failed"] = False
                return transactions

            except Exception as e:
                logger.warning(f"LLM Classification attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        # All retries exhausted — mark as failed, continue
        logger.error("LLM Classification failed after all retries. Marking batch as llm_failed.")
        for t in transactions:
            t["llm_category"] = None
            t["llm_raw_response"] = last_raw
            t["llm_failed"] = True
        return transactions

    def generate_narrative_summary(
        self, stats: Dict[str, Any], max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate a narrative summary via LLM.
        Always returns a dict — never raises. Sets llm_failed=True if all retries exhausted.
        """
        if not self.client:
            return {
                "narrative": "LLM client not configured (missing API key).",
                "risk_level": "unknown",
                "llm_failed": True,
            }

        prompt = (
            "You are an AI financial analyst.\n"
            "Analyze the following transaction statistics and return a single JSON object "
            "with EXACTLY these five keys:\n"
            "  - total_spend_by_currency: object mapping currency code to total amount (e.g. {\"INR\": 12000.0, \"USD\": 350.0})\n"
            "  - top_3_merchants: array of the top 3 merchants by spend, each with {merchant, total}\n"
            "  - anomaly_count: integer count of flagged anomalous transactions\n"
            "  - narrative: a 2-3 sentence summary of spending behavior\n"
            "  - risk_level: one of 'low', 'medium', or 'high' based on anomalies and high spends\n"
            "Do not include any other keys. Do not wrap in markdown.\n"
            f"Statistics:\n{json.dumps(stats)}\n"
        )

        last_raw: Optional[str] = None
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config=self._genai.types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
                last_raw = response.text
                result = json.loads(last_raw)
                return {
                    "narrative": result.get("narrative", ""),
                    "risk_level": result.get("risk_level", "unknown"),
                    # LLM-generated versions of the structured fields (spec compliance)
                    "llm_total_spend_by_currency": result.get("total_spend_by_currency"),
                    "llm_top_3_merchants": result.get("top_3_merchants"),
                    "llm_anomaly_count": result.get("anomaly_count"),
                    "llm_failed": False,
                }
            except Exception as e:
                logger.warning(f"LLM Narrative attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        # All retries exhausted — do NOT raise, just mark as failed
        logger.error("LLM Narrative failed after all retries. Marking as llm_failed.")
        return {
            "narrative": "Failed to generate narrative after retries.",
            "risk_level": "unknown",
            "llm_failed": True,
        }


gemini_client = GeminiClient()
