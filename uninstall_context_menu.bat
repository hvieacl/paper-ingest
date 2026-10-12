@echo off
setlocal
chcp 65001 >nul

set "PDF_KEY=HKCU\Software\Classes\SystemFileAssociations\.pdf\shell\PaperIngest"
set "DIR_KEY=HKCU\Software\Classes\Directory\shell\PaperIngest"

echo 正在移除 paper-ingest 右键菜单...
echo.

reg delete "%PDF_KEY%" /f >nul 2>&1
reg delete "%DIR_KEY%" /f >nul 2>&1

echo [DONE] 右键菜单已移除。
echo.
pause
