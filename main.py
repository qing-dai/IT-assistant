"""
main.py — Server entry point.

load_dotenv() is called here, before any project imports, so every module
that reads os.getenv() at import time sees the correct .env values.

Run with:
    python main.py
or:
    uvicorn controllers.api:app --host 0.0.0.0 --port 8000 --reload
"""
from dotenv import load_dotenv
load_dotenv()

import uvicorn

if __name__ == "__main__":
    uvicorn.run("controllers.api:app", host="0.0.0.0", port=8000, reload=True)
