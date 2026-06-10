import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.utils.data_cleaner import DataCleaner

client = TestClient(app)


# ─────────────────────────────────────────────
# DataCleaner Unit Tests
# ─────────────────────────────────────────────

class TestDataCleaner:
    def _make_df(self, overrides: dict = {}) -> pd.DataFrame:
        base = {
            "txn_id": ["T001", "T002"],
            "date": ["15-01-2024", "2024/02/20"],
            "merchant": ["Swiggy", "Amazon"],
            "amount": ["₹1,200.50", "$99.99"],
            "currency": ["inr", "usd"],
            "status": ["success", "failed"],
            "category": ["", "Shopping"],
            "account_id": ["ACC1", "ACC1"],
            "notes": ["food order", ""],
        }
        base.update(overrides)
        return pd.DataFrame(base)

    def test_dates_normalised_to_iso(self):
        df = DataCleaner.clean_and_process_dataframe(self._make_df())
        assert df["date"].iloc[0] == "2024-01-15"
        assert df["date"].iloc[1] == "2024-02-20"

    def test_currency_symbols_stripped(self):
        df = DataCleaner.clean_and_process_dataframe(self._make_df())
        assert df["amount"].iloc[0] == 1200.50
        assert df["amount"].iloc[1] == 99.99

    def test_status_uppercased(self):
        df = DataCleaner.clean_and_process_dataframe(self._make_df())
        assert df["status"].iloc[0] == "SUCCESS"
        assert df["status"].iloc[1] == "FAILED"

    def test_currency_uppercased(self):
        df = DataCleaner.clean_and_process_dataframe(self._make_df())
        assert df["currency"].iloc[0] == "INR"
        assert df["currency"].iloc[1] == "USD"

    def test_empty_category_filled_with_uncategorised(self):
        df = DataCleaner.clean_and_process_dataframe(self._make_df())
        assert df["category"].iloc[0] == "Uncategorised"
        assert df["category"].iloc[1] == "Shopping"

    def test_missing_notes_column_auto_added(self):
        df = self._make_df()
        df = df.drop(columns=["notes"])
        cleaned = DataCleaner.clean_and_process_dataframe(df)
        assert "notes" in cleaned.columns

    def test_duplicate_rows_removed(self):
        df = self._make_df()
        df = pd.concat([df, df])  # duplicate all rows
        cleaned = DataCleaner.clean_and_process_dataframe(df)
        assert len(cleaned) == 2

    def test_anomaly_3x_median(self):
        df = pd.DataFrame({
            "txn_id": ["T1", "T2", "T3"],
            "merchant": ["A", "B", "C"],
            "amount": [100.0, 100.0, 500.0],  # 500 > 3 * median(100,100,500)=100
            "currency": ["INR", "INR", "INR"],
            "account_id": ["ACC1", "ACC1", "ACC1"],
            "is_anomaly": [False, False, False],
        })
        result = DataCleaner.detect_anomalies(df)
        assert result.iloc[2]["is_anomaly"] == True
        assert "3x" in result.iloc[2]["anomaly_reason"]

    def test_anomaly_domestic_usd_case_insensitive(self):
        df = pd.DataFrame({
            "txn_id": ["T1"],
            "merchant": ["swiggy"],          # lowercase — should still be caught
            "amount": [500.0],
            "currency": ["USD"],
            "account_id": ["ACC1"],
            "is_anomaly": [False],
        })
        result = DataCleaner.detect_anomalies(df)
        assert result.iloc[0]["is_anomaly"] == True
        assert "domestic" in result.iloc[0]["anomaly_reason"].lower()

    def test_anomaly_domestic_usd_not_flagged_for_inr(self):
        df = pd.DataFrame({
            "txn_id": ["T1"],
            "merchant": ["Swiggy"],
            "amount": [500.0],
            "currency": ["INR"],             # INR is fine for domestic
            "account_id": ["ACC1"],
            "is_anomaly": [False],
        })
        result = DataCleaner.detect_anomalies(df)
        assert result.iloc[0]["is_anomaly"] == False


# ─────────────────────────────────────────────
# API Endpoint Tests (no DB / worker needed)
# ─────────────────────────────────────────────

class TestUploadEndpoint:
    def _make_csv_bytes(self, content: str) -> bytes:
        return content.encode("utf-8")

    def _valid_csv(self) -> bytes:
        return self._make_csv_bytes(
            "txn_id,date,merchant,amount,currency,status,category,account_id\n"
            "T001,15-01-2024,Amazon,500,INR,success,Shopping,ACC1\n"
        )

    def test_rejects_non_csv(self):
        response = client.post(
            "/api/v1/jobs/upload",
            files={"file": ("test.txt", b"some text", "text/plain")},
        )
        assert response.status_code == 400
        assert "CSV" in response.json()["error"]

    def test_rejects_empty_file(self):
        response = client.post(
            "/api/v1/jobs/upload",
            files={"file": ("test.csv", b"", "text/csv")},
        )
        assert response.status_code == 400
        assert "empty" in response.json()["error"].lower()

    def test_rejects_missing_columns(self):
        bad_csv = b"txn_id,date\nT001,2024-01-01\n"  # missing most required cols
        response = client.post(
            "/api/v1/jobs/upload",
            files={"file": ("test.csv", bad_csv, "text/csv")},
        )
        assert response.status_code == 400
        assert "missing" in response.json()["error"].lower()

    def test_rejects_oversized_file(self):
        # Generate > 10MB content
        big_csv = b"txn_id,date,merchant,amount,currency,status,category,account_id\n"
        big_csv += b"T001,2024-01-01,Amazon,100,INR,SUCCESS,Shopping,ACC1\n" * 200_000
        response = client.post(
            "/api/v1/jobs/upload",
            files={"file": ("big.csv", big_csv, "text/csv")},
        )
        assert response.status_code == 400
        assert "large" in response.json()["error"].lower()

    def test_job_not_found_returns_404(self):
        response = client.get("/api/v1/jobs/nonexistent-id/status")
        assert response.status_code == 404

    def test_results_not_found_returns_404(self):
        response = client.get("/api/v1/jobs/nonexistent-id/results")
        assert response.status_code == 404
