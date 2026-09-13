@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo.
echo ========================================
echo   ngrok 穿透（组员不在同一 WiFi 时用）
echo ========================================
echo.
echo 请先确保已在【另一个窗口】运行 start_frontend.bat
echo 且本机 http://127.0.0.1:8000/ 能打开。
echo.

where ngrok >nul 2>&1
if errorlevel 1 (
  echo [错误] 未找到 ngrok 命令。
  echo 1. 从 https://ngrok.com/download 下载并加入 PATH
  echo 2. 运行: ngrok config add-authtoken 你的token
  echo 3. 详见 docs\FRONTEND_REMOTE.md
  pause
  exit /b 1
)

powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 3).Content | Out-Null; Write-Host '[OK] 本机 8000 端口服务已就绪' } catch { Write-Host '[警告] 本机 8000 未响应，请先运行 scripts\start_frontend.bat'; exit 1 }"
if errorlevel 1 (
  pause
  exit /b 1
)

echo.
echo 正在启动 ngrok，请将下面 Forwarding 的 https 地址发给组员：
echo.

ngrok http 8000

pause
