

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt


# Run Streamlit app
CMD ["streamlit", "run", "Scripts.py", "--server.port=8501", "--server.address=0.0.0.0"]
