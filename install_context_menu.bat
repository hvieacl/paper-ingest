@echo off
setlocal
chcp 65001 >nul

set "SCRIPT=%~dp0load_paper.bat"
set "PDF_KEY=HKCU\Software\Classes\SystemFileAssociations\.pdf\shell\PaperIngest"
set "DIR_KEY=HKCU\Software\Classes\Directory\shell\PaperIngest"

echo 正在安装 paper-ingest 右键菜单...
echo.

reg add "%PDF_KEY%" /ve /d "导入到 paper-ingest" /f >nul
reg add "%PDF_KEY%\command" /ve /d ""%SCRIPT%" "%%1"" /f >nul

reg add "%DIR_KEY%" /ve /d "使用 paper-ingest 处理此文件夹" /f >nul
reg add "%DIR_KEY%\command" /ve /d ""%SCRIPT%" "%%1"" /f >nul

if errorlevel 1 (
  echo [ERROR] 右键菜单安装失败。
  echo 请确认当前用户有权限修改 HKCU 注册表。
  pause
  exit /b 1
)

echo [DONE] 右键菜单已安装。
echo.
echo PDF 右键：导入到 paper-ingest
echo 文件夹右键：使用 paper-ingest 处理此文件夹
echo.
echo Windows 11 如未直接显示，请点“显示更多选项”。
echo.
pause
