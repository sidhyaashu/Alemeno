import uuid
import pandas as pd

class DataCleaner:
    @staticmethod
    def clean_and_process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        df = df.drop_duplicates()
        
        df["txn_id"] = df["txn_id"].apply(
            lambda x: str(uuid.uuid4()) if pd.isna(x) or str(x).strip() == "" else str(x)
        )
        
        def parse_date(d):
            if pd.isna(d):
                return None
            d_str = str(d).strip()
            try:
                if '/' in d_str:
                    dt = pd.to_datetime(d_str, format='%Y/%m/%d')
                else:
                    dt = pd.to_datetime(d_str, format='%d-%m-%Y')
                return dt.strftime('%Y-%m-%d')
            except:
                return None
                
        df["date"] = df["date"].apply(parse_date)
        
        def clean_amount(val):
            if pd.isna(val):
                return 0.0
            val_str = str(val).replace("$", "").replace(",", "").strip()
            try:
                return float(val_str)
            except:
                return 0.0
                
        df["amount"] = df["amount"].apply(clean_amount)
        df["status"] = df["status"].apply(lambda x: str(x).upper().strip() if pd.notna(x) else None)
        df["currency"] = df["currency"].apply(lambda x: str(x).upper().strip() if pd.notna(x) else None)
        df["category"] = df["category"].apply(lambda x: "Uncategorised" if pd.isna(x) or str(x).strip() == "" else str(x).strip())
        
        return df

    @staticmethod
    def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
        account_medians = df.groupby('account_id')['amount'].median().to_dict()
        
        def detect_anomaly(row):
            is_anomaly = False
            reasons = []
            amount = row['amount']
            account = row['account_id']
            currency = row['currency']
            merchant = row['merchant']
            
            median_val = account_medians.get(account, 0)
            if median_val > 0 and amount > 3 * median_val:
                is_anomaly = True
                reasons.append("Amount > 3x account median")
                
            domestic_merchants = ['Swiggy', 'Ola', 'IRCTC']
            if currency == 'USD' and str(merchant) in domestic_merchants:
                is_anomaly = True
                reasons.append("USD used for domestic merchant")
                
            return pd.Series([is_anomaly, "; ".join(reasons)])

        df[['is_anomaly', 'anomaly_reason']] = df.apply(detect_anomaly, axis=1)
        return df
