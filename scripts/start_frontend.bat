@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8

echo.
echo ========================================
echo   AnyClaw 国际传播工作台
echo ========================================
echo.
echo [本机访问]  http://127.0.0.1:8000/
echo.

powershell -NoProfile -Command ^
  "$ips = Get-NetIPAddress -AddressFamily IPv4 ^| Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.InterfaceAlias -notmatch 'Loopback' } ^| Select-Object -ExpandProperty IPAddress; if ($ips) { $ips ^| ForEach-Object { Write-Host ('[组员访问]  http://{0}:8000/  （同一 WiFi / 局域网）' -f $_) } } else { Write-Host '[组员访问]  未检测到局域网 IP，请在本机运行 ipconfig 查看 IPv4 地址' }"

echo.
echo 提示：组员不能使用 127.0.0.1，请把上面 [组员访问] 的地址发给对方。
echo 若组员仍进不去：检查 Windows 防火墙是否允许 Python 入站，或暂时关闭专用网络防火墙测试。
echo 按 Ctrl+C 可停止服务。
echo.

python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

pause
