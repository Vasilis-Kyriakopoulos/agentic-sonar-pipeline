#!/bin/bash
# start.sh — Launch both FastAPI and Streamlit in the same container.

# Start the FastAPI backend in the background.
# Using run_server.py (with log_config=None) prevents Uvicorn from
# installing duplicate logging handlers via dictConfig().
python run_server.py &

# Start the Streamlit UI in the foreground
streamlit run ui.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
