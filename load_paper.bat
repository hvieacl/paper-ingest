@echo off
setlocal
chcp 65001 >nul
title Paper Ingest - Batch PDF to Feishu
cd /d "%~dp0"

echo ==========================================
echo        Paper Ingest V1 - Batch
echo ==========================================
echo.

if "%~1"=="" (
  echo [ERROR] 没有收到 PDF 或文件夹。
  echo.
  echo 用法：
  echo   1. 拖一篇 PDF 到 load_paper.bat
  echo   2. 同时选中多篇 PDF，一起拖到 load_paper.bat
  echo   3. 拖一个装有 PDF 的文件夹到 load_paper.bat
  echo.
  pause
  exit /b 1
)

rem 优先使用项目虚拟环境
if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  where py >nul 2>&1
  if not errorlevel 1 (
    set "PY=py -3"
  ) else (
    where python >nul 2>&1
    if not errorlevel 1 (
      set "PY=python"
    ) else (
      echo [ERROR] 没找到 Python。
      echo 请先安装 Python，或在项目目录创建 .venv。
      echo.
      pause
      exit /b 1
    )
  )
)

if not exist ".env" (
  echo [ERROR] 项目目录中没有 .env 文件。
  echo 请复制 .env.example 为 .env，并填写 DeepSeek 和飞书配置。
  echo.
  pause
  exit /b 1
)

echo [START] 开始顺序处理。批量任务期间请不要关闭窗口...
echo.
%PY% -u paper_ingest.py %*
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
  echo ==========================================
  echo [DONE] 批处理结束。
  echo ==========================================
) else (
  echo ==========================================
  echo [PARTIAL/FAILED] 批处理结束，错误码：%EXIT_CODE%
  echo 部分论文可能已经成功处理，请查看上方“批处理完成”汇总。
  echo ==========================================
)
echo.
pause
exit /b %EXIT_CODE%
