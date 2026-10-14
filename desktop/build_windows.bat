@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python -m pip install -r requirements.txt pyinstaller==6.16.0
if errorlevel 1 goto failed
.venv\Scripts\python -m unittest discover -s tests -v
if errorlevel 1 goto failed
.venv\Scripts\python -m PyInstaller --noconfirm --clean --onefile --windowed --name LSA-Data-Viewer --collect-all plotly lsa_app.py
if errorlevel 1 goto failed
dist\LSA-Data-Viewer.exe --self-test
if errorlevel 1 goto failed
echo EXE created: %CD%\dist\LSA-Data-Viewer.exe
pause
exit /b 0
:failed
echo Build failed. Read the error above.
pause
exit /b 1
