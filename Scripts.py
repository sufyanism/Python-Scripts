import streamlit as st
import pandas as pd
import re
import json
import time
import requests
from datetime import datetime
from PyPDF2 import PdfReader
from pathlib import Path

# --- Constants & Configuration ---
st.set_page_config(page_title="Academic Forensic Hub", layout="wide")
CURRENT_YEAR = datetime.now().year
TIME_OUT = 5
MAX_URLS = 100
url_regex = re.compile(r'https?://[^\s"<>()]+', re.IGNORECASE)

# --- Shared Functions ---
def extract_text_from_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()

# --- State Management ---
if 'active_task' not in st.session_state:
    st.session_state.active_task = "Staleness"

# --- Sidebar Navigation ---
st.sidebar.title("🛠️ Navigation")
if st.sidebar.button("📘 Syllabus Staleness", use_container_width=True):
    st.session_state.active_task = "Staleness"
if st.sidebar.button("🎯 Verifiability Score", use_container_width=True):
    st.session_state.active_task = "Verifiability"
if st.sidebar.button("🔍 URL Reference Check", use_container_width=True):
    st.session_state.active_task = "URL"

# --- Main Logic ---

# 1. SYLLABUS STALENESS SCANNER
if st.session_state.active_task == "Staleness":
    st.header("📘 Syllabus Staleness Scanner")
    st.write("Measures how outdated document references are.")
    
    file = st.file_uploader("Upload syllabus (.pdf, .txt)", type=["pdf", "txt"], key="staleness_file")
    
    if file:
        text = extract_text_from_pdf(file) if file.name.endswith(".pdf") else file.read().decode("utf-8")
        
        if st.button("Run Staleness Scan 🔍"):
            years = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
            years = sorted([int(y) for y in years if 1900 <= int(y) <= CURRENT_YEAR])

            if not years:
                st.error("No valid years found.")
            else:
                oldest = min(years)
                median = years[len(years)//2]
                percent_old = round((len([y for y in years if y < (CURRENT_YEAR - 10)]) / len(years)) * 100)
                score = max(0, min(100, round(100 - (percent_old * 0.7))))
                
                res = {"oldest_year": oldest, "median_year": median, "percent_old": percent_old, "score": score}
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Oldest", oldest)
                c2.metric("Median", median)
                c3.metric("% Old", f"{percent_old}%")
                c4.metric("Score", score)
                st.json(res)

# 2. LEARNING OUTCOME VERIFIABILITY
elif st.session_state.active_task == "Verifiability":
    st.header("🎯 Learning Outcome Verifiability Score")
    st.write("Analyzes Bloom's Taxonomy verbs in outcomes.")
    
    file = st.file_uploader("Upload outcomes (.txt)", type=["txt"], key="outcome_file")
    WEAK, MEDIUM, STRONG = {"understand", "know", "appreciate"}, {"explain", "analyze", "apply"}, {"design", "build", "evaluate"}

    if file:
        lines = [l.strip() for l in file.read().decode("utf-8").splitlines() if l.strip()]
        if st.button("Generate Verifiability Report 📊"):
            results = []
            total = 0
            for line in lines:
                clean = re.sub(r"^\s*\d+[\.\)\-]?\s*", "", line)
                verb = clean.split()[0].lower() if clean.split() else ""
                score = 3 if verb in STRONG else 2 if verb in MEDIUM else 1
                total += score
                results.append((clean, verb, score))
            
            perf = round((total / (len(lines) * 3)) * 100)
            st.metric("Verifiability Score", f"{perf}%")
            
            df = pd.DataFrame(results, columns=["Outcome", "Verb", "Score"])
            st.table(df)

# 3. URL REFERENCE CHECKER
elif st.session_state.active_task == "URL":
    st.header("🔍 Reference URL Checker")
    st.write("Detects 'Link Rot' in provided references.")
    
    file = st.file_uploader("Upload references (.txt)", type=["txt"], key="url_file")
    
    if file:
        text = file.read().decode("utf-8")
        urls = list(set(url_regex.findall(text)))[:MAX_URLS]
        
        if st.button("Start URL Check"):
            progress = st.progress(0)
            results = []
            for i, url in enumerate(urls):
                try:
                    r = requests.head(url, timeout=TIME_OUT, allow_redirects=True)
                    status = r.status_code
                except:
                    status = None
                
                cat = "OK" if status and 200<=status<=299 else "DEAD" if status in [404, 410] else "UNREACHABLE"
                results.append({"url": url, "status": status, "category": cat})
                progress.progress((i + 1) / len(urls))
            
            df = pd.DataFrame(results)
            st.dataframe(df)
            st.download_button("Download CSV", df.to_csv(index=False), "url_report.csv", "text/csv")
