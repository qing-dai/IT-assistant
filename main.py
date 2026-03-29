"""
main.py — Server entry point.

Run with:
    python main.py
or:
    uvicorn controllers.api:app --host 0.0.0.0 --port 8000 --reload
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("controllers.api:app", host="0.0.0.0", port=8000, reload=True)
