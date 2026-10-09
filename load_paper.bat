@echo off
setlocal
chcp 65001 >nul
title Paper Ingest - PDF to Feishu
cd /d "%~dp0"

echo ==========================================
echo        Paper Ingest V1
echo ==========================================
echo.

if "%~1"=="" (
  echo [ERROR] 没有收到 PDF。
  echo 请把 PDF 文件直接拖到 load_paper.bat 上。
  echo.
  pause
  exit /b 1
)

echo [PDF] %~1
echo.

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

echo [START] 正在启动，请不要关闭窗口...
echo.
%PY% -u paper_ingest.py "%~1"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
  echo ==========================================
  echo [DONE] 任务结束。
  echo ==========================================
) else (
  echo ==========================================
  echo [FAILED] 运行失败，错误码：%EXIT_CODE%
  echo 请把上方最后一段报错截图发给我。
  echo ==========================================
)
echo.
pause
exit /b %EXIT_CODE%
