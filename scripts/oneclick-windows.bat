@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo 正在启动一键部署...
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0oneclick-windows.ps1"
if errorlevel 1 pause
