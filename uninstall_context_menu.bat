@echo off
setlocal
chcp 65001 >nul

set "PDF_LOAD_KEY=HKCU\Software\Classes\SystemFileAssociations\.pdf\shell\PaperIngest"
set "PDF_SYNC_KEY=HKCU\Software\Classes\SystemFileAssociations\.pdf\shell\PaperIngestSync"
set "PDF_RERUN_KEY=HKCU\Software\Classes\SystemFileAssociations\.pdf\shell\PaperIngestRerun"
set "DIR_KEY=HKCU\Software\Classes\Directory\shell\PaperIngest"

echo 正在移除 paper-ingest 右键菜单...
echo.

reg delete "%PDF_LOAD_KEY%" /f >nul 2>&1
reg delete "%PDF_SYNC_KEY%" /f >nul 2>&1
reg delete "%PDF_RERUN_KEY%" /f >nul 2>&1
reg delete "%DIR_KEY%" /f >nul 2>&1

echo [DONE] 右键菜单已移除。
echo.
pause
