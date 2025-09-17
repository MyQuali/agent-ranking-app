import io
import json
import streamlit as st
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from parser import extract_text, parse_totals, build_dataframe

# 🔒 Leadership Password Gate (Render-compatible: uses ENV, not secrets.toml)
def check_password():
    pw = os.environ.get("APP_PASSWORD")  # set this in Render → Environment
    if not pw:  # if not set, skip protection
        return True
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
    if st.session_state.auth_ok:
        return True

    with st.form("login"):
        typed = st.text_input("Password", type="password")
        ok = st.form_submit_button("Enter")
        if ok and typed == pw:
            st.session_state.auth_ok = True
            return True

    st.stop()  # halt app until correct password entered

check_password()
# 🔒 End Password Gate

# --- Streamlit App Starts Here ---
st.set_page_config(page_title="Agent Ranking PDF Parser", layout="wide")

st.title("Agent Ranking PDF Parser")
st.caption("Upload competitor reports and export ranked CSV + PDF with totals.")

with st.expander("Instructions", expanded=False):
    st.markdown(
        """
        1. Upload one or more PDFs that contain **'Production for <Agent>'** sections with a **'Total'** line.  
        2. *(Optional)* Paste a JSON object of name fixes (e.g., `{ "Ry an Preston": "Ryan Preston" }`).  
        3. Click **Process PDFs** to parse, rank, and export results.  
        """
    )

uploaded_files = st.file_uploader("Upload competitor PDF(s)", type=["pdf"], accept_multiple_files=True)
name_fixes_text = st.text_area("Optional: Name fixes JSON", height=120, placeholder='{"Ry an Preston": "Ryan Preston"}')
custom_fixes = {}
if name_fixes_text.strip():
    try:
        custom_fixes = json.loads(name_fixes_text)
    except Exception as e:
        st.warning(f"Invalid JSON. Error: {e}")

def build_pdf_bytes(title: str, df: pd.DataFrame) -> bytes:
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 12))

    total_tx = int(df["Transactions"].sum())
    total_vol = int(df["Sold Volume"].sum())

    table_data = [["Agent", "Transactions", "Sold Volume"]]
    for _, row in df.iterrows():
        table_data.append([row["Agent"], str(int(row["Transactions"])), f"${int(row['Sold Volume']):,}"])
    table_data.append(["TOTAL", str(total_tx), f"${total_vol:,}"])

    table = Table(table_data, colWidths=[260, 110, 160])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.whitesmoke, colors.lightgrey]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
    ]))

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=landscape(letter))
    elements.append(table)
    doc.build(elements)
    buff.seek(0)
    return buff.read()

if st.button("Process PDFs") and uploaded_files:
    for up in uploaded_files:
        st.subheader(up.name)
        try:
            text = extract_text(up)
            records = parse_totals(text)
            df = build_dataframe(records, custom_fixes=custom_fixes)
            if df.empty:
                st.error("No agent totals found in this PDF.")
                continue

            st.dataframe(df, use_container_width=True)
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            pdf_bytes = build_pdf_bytes(f"{up.name} – Agent Rankings (with Totals)", df)

            st.download_button("⬇️ Download CSV", data=csv_bytes, file_name=up.name.replace(".pdf","_ranked.csv"), mime="text/csv")
            st.download_button("⬇️ Download PDF", data=pdf_bytes, file_name=up.name.replace(".pdf","_ranked.pdf"), mime="application/pdf")
        except Exception as e:
            st.error(f"Error processing {up.name}: {e}")
elif uploaded_files:
    st.info("Click **Process PDFs** to parse your uploads.")
else:
    st.info("Upload one or more competitor PDFs to get started.")
