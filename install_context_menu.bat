@echo off
setlocal
chcp 65001 >nul

set "LOAD_SCRIPT=%~dp0load_paper.bat"
set "SYNC_SCRIPT=%~dp0sync_paper.bat"
set "RERUN_SCRIPT=%~dp0rerun_paper.bat"

set "PDF_LOAD_KEY=HKCU\Software\Classes\SystemFileAssociations\.pdf\shell\PaperIngest"
set "PDF_SYNC_KEY=HKCU\Software\Classes\SystemFileAssociations\.pdf\shell\PaperIngestSync"
set "PDF_RERUN_KEY=HKCU\Software\Classes\SystemFileAssociations\.pdf\shell\PaperIngestRerun"
set "DIR_KEY=HKCU\Software\Classes\Directory\shell\PaperIngest"

echo 正在安装 paper-ingest 右键菜单...
echo.

reg add "%PDF_LOAD_KEY%" /ve /d "导入到 paper-ingest" /f >nul
reg add "%PDF_LOAD_KEY%\command" /ve /d "\"%LOAD_SCRIPT%\" \"%%1\"" /f >nul

reg add "%PDF_SYNC_KEY%" /ve /d "使用缓存覆盖飞书" /f >nul
reg add "%PDF_SYNC_KEY%\command" /ve /d "\"%SYNC_SCRIPT%\" \"%%1\"" /f >nul

reg add "%PDF_RERUN_KEY%" /ve /d "重新分析并覆盖飞书" /f >nul
reg add "%PDF_RERUN_KEY%\command" /ve /d "\"%RERUN_SCRIPT%\" \"%%1\"" /f >nul

reg add "%DIR_KEY%" /ve /d "使用 paper-ingest 处理此文件夹" /f >nul
reg add "%DIR_KEY%\command" /ve /d "\"%LOAD_SCRIPT%\" \"%%1\"" /f >nul

if errorlevel 1 (
  echo [ERROR] 右键菜单安装失败。
  echo 请确认当前用户有权限修改 HKCU 注册表。
  pause
  exit /b 1
)

echo [DONE] 右键菜单已安装。
echo.
echo PDF 右键：
echo   - 导入到 paper-ingest
echo   - 使用缓存覆盖飞书
echo   - 重新分析并覆盖飞书
echo.
echo 文件夹右键：
echo   - 使用 paper-ingest 处理此文件夹
echo.
echo 为避免误操作，文件夹右键不会提供“重新分析并覆盖”。
echo Windows 11 如未直接显示，请点“显示更多选项”。
echo.
pause
