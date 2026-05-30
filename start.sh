#!/bin/bash
# start.sh — Launch both FastAPI and Streamlit in the same container.

# Start the FastAPI backend in the background
uvicorn api:app --host 0.0.0.0 --port 8000 &

# Start the Streamlit UI in the foreground
streamlit run ui.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
