@echo off
chcp 65001 >nul
title 大理州动物防疫物资管理软件 - Windows打包工具
echo ============================================
echo   大理州动物防疫物资管理软件 - Windows打包
echo ============================================
echo.

REM 检查是否安装了Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    echo 安装时记得勾选 "Add Python to PATH"
    pause
    exit /b 1
)
echo [OK] Python 已安装

REM 检查是否安装了pip
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] pip 未安装
    pause
    exit /b 1
)
echo [OK] pip 已安装

echo.
echo [1/3] 安装依赖包...
pip install flask flask-sqlalchemy flask-login flask-wtf wtforms
pip install openpyxl pandas bcrypt pywebview
pip install pyinstaller
echo [OK] 依赖安装完成

echo.
echo [2/3] 清理旧的打包文件...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q "*.spec"
echo [OK] 清理完成

echo.
echo [3/3] 开始打包，请耐心等待（约2-5分钟）...
echo.

REM Windows专用打包命令 - 独立exe，带控制台窗口
pyinstaller --onefile ^
    --name "大理州动物防疫物资管理软件" ^
    --add-data "app;app" ^
    --add-data "config.py;." ^
    --hidden-import app ^
    --hidden-import app.models ^
    --hidden-import app.models.user ^
    --hidden-import app.models.material ^
    --hidden-import app.models.record ^
    --hidden-import app.models.setting ^
    --hidden-import app.routes ^
    --hidden-import app.routes.auth_routes ^
    --hidden-import app.routes.inventory_routes ^
    --hidden-import app.routes.main_routes ^
    --hidden-import app.routes.record_routes ^
    --hidden-import app.routes.report_routes ^
    --hidden-import app.routes.setting_routes ^
    --hidden-import config ^
    --hidden-import sqlalchemy ^
    --hidden-import flask_sqlalchemy ^
    --hidden-import flask_login ^
    --hidden-import flask_wtf ^
    --hidden-import wtforms ^
    --hidden-import wtforms.validators ^
    --hidden-import wtforms.fields ^
    --hidden-import wtforms.csrf ^
    --hidden-import pandas ^
    --hidden-import openpyxl ^
    --hidden-import bcrypt ^
    --hidden-import html.parser ^
    --hidden-import email ^
    --hidden-import email.mime ^
    --hidden-import email.mime.multipart ^
    --hidden-import email.mime.text ^
    --hidden-import email.mime.base ^
    --hidden-import pywebview ^
    --hidden-import webview ^
    --hidden-import bottle ^
    --exclude-module tkinter ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    --exclude-module PIL ^
    --exclude-module cv2 ^
    --exclude-module PyQt5 ^
    --exclude-module PySide2 ^
    --exclude-module PySide6 ^
    run.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 打包失败！请检查上面的错误信息。
    pause
    exit /b 1
)

echo.
echo ============================================
echo   [打包成功！]
echo ============================================
echo.
echo   生成文件:
echo   dist\大理州动物防疫物资管理软件.exe
echo.
echo   使用方法：
echo     双击 exe 即可启动（桌面窗口模式）
echo.
echo   管理员账号：admin / admin123
echo.
echo   提示：数据文件（数据库、导入导出）保存在
echo   exe 同目录下的 data\ 文件夹中
echo.
pause
