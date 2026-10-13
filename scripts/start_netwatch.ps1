$ProjectRoot = "C:\Users\gusta\Documents\Projects\NetWatch"
$Python = "$ProjectRoot\.venv\Scripts\python.exe"

Start-Process `
    -FilePath $Python `
    -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden