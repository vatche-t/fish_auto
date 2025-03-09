import pandas as pd


def get_email(national_code, csv_path="data/contacts.csv"):
    df = pd.read_csv(csv_path, dtype=str)
    record = df.loc[df["national_code"] == national_code]
    return record.iloc[0]["email"] if not record.empty else None
