---
description: Start the OraTek Streamlit app with the project virtual environment
---

# Start OraTek

Start the OraTek Streamlit app from the repository root.

## Workflow

1. Use the repository root `C:\reository\21EMAStructure`.
2. Use the project virtual environment only: `.\.venv\Scripts\python.exe`.
3. Do not use system Python or global `streamlit.exe`.
4. If port `8501` is already in use, identify the owning process first.
5. If the process is a stale OraTek/Streamlit process using system Python, ask before stopping it.
6. If the correct app is already running, report the URL instead of starting a duplicate.
7. Start the app with:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app\main.py
```

8. After startup, report the local URL, usually `http://localhost:8501`.
