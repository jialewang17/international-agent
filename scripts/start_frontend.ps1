# 局域网启动（PowerShell）
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"

Write-Host ""
Write-Host "========================================"
Write-Host "  AnyClaw 国际传播工作台"
Write-Host "========================================"
Write-Host ""
Write-Host "[本机访问]  http://127.0.0.1:8000/"
Write-Host ""

$ips = Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object {
    $_.IPAddress -notlike "127.*" -and
    $_.IPAddress -notlike "169.254.*" -and
    $_.InterfaceAlias -notmatch "Loopback"
  } |
  Select-Object -ExpandProperty IPAddress

if ($ips) {
  foreach ($ip in $ips) {
    Write-Host "[组员访问]  http://${ip}:8000/  （同一 WiFi / 局域网）"
  }
} else {
  Write-Host "[组员访问]  未检测到局域网 IP，请运行 ipconfig 查看 IPv4"
}

Write-Host ""
Write-Host "组员不能使用 127.0.0.1；防火墙拦 8000 时请在 Windows 防火墙中允许 Python。"
Write-Host "按 Ctrl+C 停止服务。"
Write-Host ""

python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
