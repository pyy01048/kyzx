@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
echo 启动 研讯 YanXun ... 浏览器访问 http://127.0.0.1:8000
call conda run -n pyy --no-capture-output python run.py
endlocal
