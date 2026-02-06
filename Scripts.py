import streamlit as st
import pandas as pd
import re
import json
import time
import requests
from datetime import datetime
from PyPDF2 import PdfReader
from pathlib import Path
import base64

# Extra imports for DOC/DOCX
from docx import Document
import textract

# ------------------ 1. Configuration ------------------
st.set_page_config(page_title="Zeba Academy", layout="wide", initial_sidebar_state="collapsed")

# ------------------ 2. Custom CSS ------------------
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stDecoration"] {display: none;}

    /* Hide Sidebar entirely since we use top buttons */
    [data-testid="stSidebar"] {display: none;}

    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 2rem;
        border-bottom: 2px solid #f0f2f6;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 70px;
        z-index: 9999;
    }

    .logo-text {
        font-size: 24px;
        font-weight: bold;
        color: #0e1117;
    }

    .block-container {
        padding-top: 100px;
    }

    .footer-container {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f8f9fa;
        color: #31333F;
        text-align: center;
        padding: 8px 0;
        font-weight: 500;
        border-top: 1px solid #dee2e6;
        z-index: 1000001;
    }
    
    /* Style for the active/inactive buttons */
    .stButton button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #f0f2f6;
    }
</style>
""", unsafe_allow_html=True)

# ------------------ 3. Header & Footer ------------------
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

img_base64 = get_base64_image("./Logo.png")

st.markdown(f"""
<div class="header-container">
    <div class="logo-text">Zeba Academy</div>
    <div>
        {"<img src='data:image/png;base64," + img_base64 + "' height='50'/>" if img_base64 else ""}
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="footer-container">
    © 2026 Zeba Academy | Empowering Academic Integrity
</div>
""", unsafe_allow_html=True)

# ------------------ 4. State Management ------------------
if "active_task" not in st.session_state:
    st.session_state.active_task = "Staleness"

# ------------------ 5. Top Navigation Buttons ------------------
# This replaces the sidebar
nav_col1, nav_col2, nav_col3 = st.columns(3)

with nav_col1:
    if st.button("📘 Syllabus Staleness", use_container_width=True):
        st.session_state.active_task = "Staleness"
        st.rerun()

with nav_col2:
    if st.button("🎯 Verifiability Score", use_container_width=True):
        st.session_state.active_task = "Verifiability"
        st.rerun()

with nav_col3:
    if st.button("🔍 URL Reference Check", use_container_width=True):
        st.session_state.active_task = "URL"
        st.rerun()

st.markdown("---")

# ------------------ 6. Helper Functions ------------------
def extract_text_from_file(uploaded_file):
    filename = uploaded_file.name.lower()
    if filename.endswith(".txt"):
        return uploaded_file.read().decode("utf-8", errors="ignore")
    elif filename.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    elif filename.endswith(".docx"):
        doc = Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])
    elif filename.endswith(".doc"):
        temp_path = f"temp_{int(time.time())}.doc"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())
        try:
            text = textract.process(temp_path).decode("utf-8", errors="ignore")
        finally:
            Path(temp_path).unlink(missing_ok=True)
        return text
    return ""

CURRENT_YEAR = datetime.now().year
TIME_OUT = 5
MAX_URLS = 100
url_regex = re.compile(r'https?://[^\s"<>()]+', re.IGNORECASE)

# ------------------ 7. Modules ------------------

# 📘 STALENESS
if st.session_state.active_task == "Staleness":
    st.header("📘 Syllabus Staleness Scanner")
    file = st.file_uploader("Upload (.pdf, .docx, .doc, .txt)", type=["pdf", "docx", "doc", "txt"])

    if file and st.button("Run Staleness Scan 🔍"):
        text = extract_text_from_file(file)
        years = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
        years = sorted([int(y) for y in years if 1900 <= int(y) <= CURRENT_YEAR])

        if not years:
            st.error("No valid years found.")
        else:
            oldest = min(years)
            median = years[len(years)//2]
            percent_old = round((len([y for y in years if y < (CURRENT_YEAR - 10)]) / len(years)) * 100)
            score = max(0, min(100, round(100 - (percent_old * 0.7))))

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Oldest", oldest)
            c2.metric("Median", median)
            c3.metric("% Old", f"{percent_old}%")
            c4.metric("Score", score)

# 🎯 VERIFIABILITY
elif st.session_state.active_task == "Verifiability":
    st.header("🎯 Learning Outcome Verifiability")
    st.write("Extracts measurable outcomes and ignores administrative text.")
    
    file = st.file_uploader("Upload outcomes document", type=["docx", "doc", "txt"])

    WEAK = {"understand", "know", "appreciate", "learn", "familiarize", "study"}
    MEDIUM = {"explain", "analyze", "apply", "describe", "identify", "demonstrate"}
    STRONG = {"design", "build", "evaluate", "create", "synthesize", "construct"}
    ALL_VERBS = WEAK.union(MEDIUM).union(STRONG)

    if file and st.button("Generate Bulleted Report 📊"):
        text = extract_text_from_file(file)
        raw_lines = text.splitlines()
        filtered_outcomes = []
        total_score = 0

        for line in raw_lines:
            line = line.strip()
            if not line: continue
            clean_line = re.sub(r"^(Outcome|LO)?\s*[\d\.\)\-\*•]+\s*:?", "", line, flags=re.IGNORECASE).strip()
            if not clean_line: continue
            words = clean_line.split()
            first_word = words[0].lower() if words else ""
            if first_word in ALL_VERBS:
                score = 3 if first_word in STRONG else 2 if first_word in MEDIUM else 1
                total_score += score
                filtered_outcomes.append(clean_line)

        if not filtered_outcomes:
            st.warning("No learning outcomes starting with standard action verbs were detected.")
        else:
            perf = round((total_score / (len(filtered_outcomes) * 3)) * 100)
            st.metric("Verifiability Score", f"{perf}%")
            st.markdown("---")
            st.subheader("📋 Extracted Learning Outcomes")
            for outcome in filtered_outcomes:
                st.markdown(f"* {outcome}")

# 🔍 URL CHECKER
elif st.session_state.active_task == "URL":
    st.header("🔍 Reference URL Checker")
    file = st.file_uploader("Upload (.pdf, .docx, .doc, .txt)", type=["pdf", "docx", "doc", "txt"])

    if file and st.button("Start URL Check"):
        text = extract_text_from_file(file)
        urls = list(set(url_regex.findall(text)))[:MAX_URLS]
        progress = st.progress(0)
        results = []

        for i, url in enumerate(urls):
            try:
                r = requests.head(url, timeout=TIME_OUT, allow_redirects=True)
                status = r.status_code
            except:
                status = None
            cat = "OK" if status and 200 <= status <= 299 else "DEAD" if status in [404, 410] else "UNREACHABLE"
            results.append({"url": url, "status": status, "category": cat})
            progress.progress((i + 1) / len(urls))

        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True)
        st.markdown(f"**Summary:** {len(df[df['category'] == 'OK'])} OK, {len(df[df['category'] == 'DEAD'])} DEAD, {len(df[df['category'] == 'UNREACHABLE'])} UNREACHABLE")

