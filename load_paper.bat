@echo off
chcp 65001 >nul
cd /d "%~dp0"
if "%~1"=="" (
  echo 请把 PDF 文件拖到这个 bat 文件上。
  pause
  exit /b 1
)
python paper_ingest.py "%~1"
echo.
pause
