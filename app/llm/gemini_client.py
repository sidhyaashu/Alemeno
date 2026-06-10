import json
import time
import logging
from typing import List, Dict, Any
from google import genai
from app.core.config import settings
from app.core.exceptions import LLMIntegrationException

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        try:
            # Assumes GEMINI_API_KEY is available via env or settings
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")
            self.client = None

    def classify_transactions_batch(self, transactions: List[Dict[str, Any]], max_retries=3) -> List[Dict[str, Any]]:
        if not self.client or not transactions:
            for t in transactions:
                t["llm_failed"] = True
            return transactions

        prompt = (
            "You are a financial transaction classification AI.\n"
            "Assign exactly one category to each transaction from this list: "
            "Food, Shopping, Travel, Transport, Utilities, Cash Withdrawal, Entertainment, Other.\n"
            "Return the output strictly as a JSON array of objects with keys 'txn_id' and 'category'.\n"
            f"Transactions:\n{json.dumps(transactions)}\n"
        )

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
                result = json.loads(response.text)
                result_map = {item["txn_id"]: item.get("category", "Other") for item in result if "txn_id" in item}
                
                for t in transactions:
                    t["llm_category"] = result_map.get(t["txn_id"], "Other")
                    t["llm_failed"] = False
                return transactions
            except Exception as e:
                logger.warning(f"LLM Classification attempt {attempt + 1} failed: {e}")
                time.sleep(2 ** attempt)

        # Fallback
        for t in transactions:
            t["llm_failed"] = True
        return transactions

    def generate_narrative_summary(self, stats: Dict[str, Any], max_retries=3) -> Dict[str, Any]:
        if not self.client:
            return {"narrative": "LLM client not configured or failed to init.", "risk_level": "unknown"}
            
        prompt = (
            "You are an AI financial analyst.\n"
            "Analyze the following transaction statistics and generate a 2-3 sentence narrative summary "
            "of the user's spending behavior, and assign a 'risk_level' (low, medium, or high) based on anomalies and high spends.\n"
            "Return strictly a JSON object with keys 'narrative' and 'risk_level'.\n"
            f"Statistics: {json.dumps(stats)}\n"
        )

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
                result = json.loads(response.text)
                return {
                    "narrative": result.get("narrative", ""),
                    "risk_level": result.get("risk_level", "unknown")
                }
            except Exception as e:
                logger.warning(f"LLM Narrative attempt {attempt + 1} failed: {e}")
                time.sleep(2 ** attempt)

        raise LLMIntegrationException("Failed to generate narrative after retries.")

gemini_client = GeminiClient()
