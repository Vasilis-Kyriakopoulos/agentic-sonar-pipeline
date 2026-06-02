"""
run_server.py — Start the FastAPI app via Uvicorn programmatically.

Using log_config=None prevents Uvicorn from calling dictConfig(),
which would add duplicate StreamHandlers to the root logger.
All logging is handled by the app's own configure_clean_logging().
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        log_config=None,
    )
