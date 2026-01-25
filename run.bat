@echo off
echo 启动网恋安全卫士...

:: 检查环境变量
if "%OPENROUTER_API_KEY%"=="" (
    echo 警告: 未设置 OPENROUTER_API_KEY 环境变量
    echo 请先设置环境变量: set OPENROUTER_API_KEY=你的API密钥
    echo 或者编辑此文件，取消注释下面的行并填入你的API密钥
    echo.
    pause
    exit /b 1
)

:: 如果需要硬编码（不推荐），请取消注释下面这行并填入你的API密钥
:: set OPENROUTER_API_KEY=你的API密钥

:: 启动后端
start "Backend" cmd /k "cd /d e:\0000AI\watcha\server && python main.py"

:: 等待后端启动
timeout /t 3 /nobreak

:: 启动前端
start "Frontend" cmd /k "cd /d e:\0000AI\watcha\web && npm run dev"

echo 服务已启动！
echo 后端: http://localhost:8000
echo 前端: http://localhost:5173