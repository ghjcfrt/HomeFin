@echo off
chcp 65001 >nul
setlocal

REM 临时切换到 UTF-8，减少 CMD 中文乱码
for /f "tokens=2 delims=: " %%a in ('chcp') do set "_OLD_CP=%%a"
chcp 65001 >nul

REM 设置项目关键目录与 Python 虚拟环境解释器
set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "VENV_PY=%ROOT_DIR%.venv\Scripts\python.exe"

echo 正在启动 HomeFin 本地测试环境...

REM 启动前先检查后端与前端入口文件是否存在
if not exist "%BACKEND_DIR%\app\main.py" (
  echo [ERROR] 未找到后端入口文件："%BACKEND_DIR%\app\main.py"
  pause
  exit /b 1
)

if not exist "%FRONTEND_DIR%\index.html" (
  echo [ERROR] 未找到前端入口文件："%FRONTEND_DIR%\index.html"
  pause
  exit /b 1
)


REM 检查虚拟环境路径是否包含中文字符
echo %ROOT_DIR% | findstr /r /c:"[一-龥]" >nul
if not errorlevel 1 (
  echo [ERROR] 路径 "%ROOT_DIR%" 含有中文字符，无法创建虚拟环境，请将项目放在无中文路径下。
  pause
  exit /b 1
)

if not exist "%VENV_PY%" (
  echo [INFO] 正在创建虚拟环境："%ROOT_DIR%.venv"
  python -m venv "%ROOT_DIR%.venv"
)

REM 检测用户地区，自动切换 pip 源

REM 通过外网IP判断是否在中国大陆
set "PIP_INDEX_URL="
for /f "delims=" %%i in ('powershell -Command "try { (Invoke-RestMethod -Uri 'https://ipinfo.io/json' -UseBasicParsing).country } catch { '' }"") do set "_COUNTRY=%%i"
if /i "%_COUNTRY%"=="CN" set "PIP_INDEX_URL=--index-url https://mirrors.aliyun.com/pypi/simple/"


uv pip install --python "%VENV_PY%" %PIP_INDEX_URL% -r "%BACKEND_DIR%\requirements.txt"
if errorlevel 1 (
  echo [ERROR] 依赖安装失败，请检查网络或权限问题。
  pause
  exit /b 1
)

start "HomeFin 后端" cmd /k "cd /d ""%BACKEND_DIR%"" && ""%VENV_PY%"" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

start "HomeFin 前端" cmd /k "cd /d ""%FRONTEND_DIR%"" && python -m http.server 5500"

timeout /t 2 /nobreak >nul
start "" "http://localhost:5500"

echo.
echo 后端文档:  http://localhost:8000/docs
echo 前端地址:  http://localhost:5500
echo.
echo 已打开两个新的终端窗口。关闭它们即可停止服务。

if defined _OLD_CP chcp %_OLD_CP% >nul
endlocal
pause
