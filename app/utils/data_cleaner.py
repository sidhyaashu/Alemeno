import uuid
import logging
import pandas as pd

logger = logging.getLogger(__name__)

# Domestic-only merchants that should never have USD transactions
DOMESTIC_MERCHANTS = {"swiggy", "ola", "irctc", "zomato", "rapido", "meesho"}


class DataCleaner:
    @staticmethod
    def clean_and_process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        # Ensure optional columns exist to avoid KeyError downstream
        for col in ["notes", "category"]:
            if col not in df.columns:
                df[col] = ""

        # Remove exact duplicate rows
        df = df.drop_duplicates()

        # Fill missing txn_id with a generated UUID
        df["txn_id"] = df["txn_id"].apply(
            lambda x: str(uuid.uuid4()) if pd.isna(x) or str(x).strip() == "" else str(x)
        )

        # Robust date normalisation to ISO 8601
        df["date"] = df["date"].apply(DataCleaner._parse_date)

        # Strip currency symbols, commas; coerce invalid to NaN (not 0)
        df["amount"] = df["amount"].apply(DataCleaner._clean_amount)

        # Uppercase status and currency
        df["status"] = df["status"].apply(
            lambda x: str(x).upper().strip() if pd.notna(x) and str(x).strip() else None
        )
        df["currency"] = df["currency"].apply(
            lambda x: str(x).upper().strip() if pd.notna(x) and str(x).strip() else None
        )

        # Fill missing / empty categories
        df["category"] = df["category"].apply(
            lambda x: "Uncategorised" if pd.isna(x) or str(x).strip() == "" else str(x).strip()
        )

        return df

    @staticmethod
    def _parse_date(d) -> str | None:
        """Parse any reasonable date string to YYYY-MM-DD."""
        if pd.isna(d):
            return None
        d_str = str(d).strip()
        if not d_str:
            return None
        try:
            # pandas infer_datetime_format handles a very wide range of formats
            dt = pd.to_datetime(d_str, infer_datetime_format=True, dayfirst=True)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            logger.warning(f"Could not parse date: '{d_str}' — storing as None")
            return None

    @staticmethod
    def _clean_amount(val) -> float | None:
        """Strip currency symbols / commas and return a float. Returns None for truly unparseable values."""
        if pd.isna(val):
            return None
        val_str = (
            str(val)
            .replace("$", "")
            .replace("₹", "")
            .replace("€", "")
            .replace("£", "")
            .replace(",", "")
            .strip()
        )
        try:
            return float(val_str)
        except ValueError:
            logger.warning(f"Invalid amount value: '{val}' — storing as None")
            return None

    @staticmethod
    def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
        # Drop rows where amount is None before computing median
        valid_df = df.dropna(subset=["amount"])
        account_medians = valid_df.groupby("account_id")["amount"].median().to_dict()

        def detect_anomaly(row):
            is_anomaly = False
            reasons = []
            amount = row.get("amount")
            account = row.get("account_id")
            currency = row.get("currency")
            merchant = str(row.get("merchant", "") or "")

            if amount is not None:
                median_val = account_medians.get(account, 0)
                if median_val > 0 and amount > 3 * median_val:
                    is_anomaly = True
                    reasons.append("Amount > 3x account median")

            # Case-insensitive domestic merchant check
            if currency == "USD" and merchant.lower() in DOMESTIC_MERCHANTS:
                is_anomaly = True
                reasons.append("USD used for domestic merchant")

            return pd.Series([is_anomaly, "; ".join(reasons) if reasons else None])

        df[["is_anomaly", "anomaly_reason"]] = df.apply(detect_anomaly, axis=1)
        return df
