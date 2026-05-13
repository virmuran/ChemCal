@echo off
chcp 65001 >nul
title CalcE (看门狗模式)
echo 正在启动 CalcE 看门狗...
echo 崩溃后自动重启（最多 3 次/5 分钟）
echo.
"%~dp0launcher.py"
pause
