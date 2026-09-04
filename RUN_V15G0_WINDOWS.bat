@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "PAD_Stream_V15G0_End_to_End_PAD_Stream_Integration_PORTABLE.py"
) else (
    python "PAD_Stream_V15G0_End_to_End_PAD_Stream_Integration_PORTABLE.py"
)
if errorlevel 1 pause
endlocal
