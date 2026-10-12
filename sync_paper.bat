@echo off
setlocal
chcp 65001 >nul
title Paper Ingest - Sync Cached Result

if "%~1"=="" (
  echo [ERROR] 没有收到 PDF 文件。
  echo.
  echo 用法：右键单篇 PDF ^> 使用缓存覆盖飞书
  echo.
  pause
  exit /b 1
)

echo ==========================================
echo      Paper Ingest - Sync Cached Result
echo ==========================================
echo.
echo 将复用现有 AI 缓存，并覆盖飞书中的同 PaperHash 记录。
echo 不会强制重新调用 DeepSeek。
echo.

call "%~dp0load_paper.bat" "%~1" --update
exit /b %ERRORLEVEL%
