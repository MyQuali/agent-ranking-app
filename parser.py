
import re
import pandas as pd
from PyPDF2 import PdfReader

def extract_text(pdf_file):
    """
    Accepts a file-like object or path. Returns the concatenated text of all pages.
    """
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        txt = page.extract_text() or ""
        text += txt + "\n"
    return text

def parse_totals(text: str):
    """
    Parse 'Production for <Agent>' sections and read the 'Total <count> $<list> $<sold>' line.
    Returns list of (agent, count, sold_volume).
    """
    lines = text.splitlines()
    data = []
    current_agent = None
    for line in lines:
        if line.startswith("Production for "):
            current_agent = line.replace("Production for ", "").strip()
        elif current_agent and line.strip().startswith("Total "):
            parts = line.split()
            try:
                count = int(parts[1])
                sold_volume_token = parts[3]  # e.g., $7,947,900
                sold_volume = int(sold_volume_token.replace("$","").replace(",",""))
                data.append((current_agent, count, sold_volume))
            except Exception:
                pass
            current_agent = None
    return data

def basic_clean_name(name: str) -> str:
    name = name.replace("\\nCount List", " ").replace("\\n", " ").strip()
    name = re.sub(r"\\s+", " ", name)
    return name

def build_dataframe(records, custom_fixes=None):
    custom_fixes = custom_fixes or {}
    df = pd.DataFrame(records, columns=["Agent", "Transactions", "Sold Volume"])
    if df.empty:
        return df
    df["Agent"] = df["Agent"].apply(basic_clean_name)
    if custom_fixes:
        df["Agent"] = df["Agent"].apply(lambda n: custom_fixes.get(n, n))
    df = df.sort_values(by="Sold Volume", ascending=False).reset_index(drop=True)
    return df
