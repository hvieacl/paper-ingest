@echo off
setlocal
chcp 65001 >nul
title Paper Ingest - Force Reanalyze

if "%~1"=="" (
  echo [ERROR] 没有收到 PDF 文件。
  echo.
  echo 用法：右键单篇 PDF ^> 重新分析并覆盖飞书
  echo.
  pause
  exit /b 1
)

echo ==========================================
echo      Paper Ingest - FORCE REANALYZE
echo ==========================================
echo.
echo [WARN] 将忽略现有 AI 缓存，重新调用 DeepSeek。
echo [WARN] 新结果会覆盖本地 cache，并覆盖飞书中的同 PaperHash 记录。
echo [WARN] 本次操作会产生新的 API 消耗。
echo.

call "%~dp0load_paper.bat" "%~1" --force-ai --update
exit /b %ERRORLEVEL%
