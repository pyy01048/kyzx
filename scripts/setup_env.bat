@echo off
chcp 65001 >nul
setlocal
echo ============================================
echo  研讯 YanXun - 创建 conda 环境 pyy
echo ============================================

where conda >nul 2>nul
if errorlevel 1 (
  echo [错误] 没找到 conda，请先把 Anaconda/Miniconda 加入 PATH
  exit /b 1
)

conda env list | findstr /b /c:"pyy " >nul
if errorlevel 1 (
  echo [1/2] 创建环境 pyy ...
  call conda create -n pyy python=3.11 -y
) else (
  echo [1/2] 环境 pyy 已存在，跳过创建
)

echo [2/2] 安装依赖 ...
call conda run -n pyy python -m pip install -r "%~dp0..\requirements.txt"
if errorlevel 1 (
  echo [错误] 依赖安装失败
  exit /b 1
)

echo.
echo 完成。双击 run.bat 或执行：conda run -n pyy python run.py
endlocal
