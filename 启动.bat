@echo off
chcp 65001 >nul
title 大理州动物防疫物资管理软件

echo ========================================
echo   大理州动物防疫物资管理软件
echo   正在启动独立窗口...
echo ========================================
echo.

setlocal enabledelayedexpansion

if "%PORT%"=="" (
    set PORT=5000
)

:: 独立窗口模式启动（无需浏览器）
大理州动物防疫物资管理软件.exe

pause
