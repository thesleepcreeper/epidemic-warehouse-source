#!/bin/bash
# 大理州动物防疫物资管理软件 - Linux/Mac 启动脚本

echo "========================================"
echo "  大理州动物防疫物资管理软件 - 启动"
echo "========================================"
echo ""
echo "启动后访问: http://127.0.0.1:5000"
echo "管理员账号: admin / admin123"
echo ""
echo "按 Ctrl+C 停止服务"
echo "========================================"
echo ""

# 尝试 python3，失败则用 python
python3.11 run.py 2>/dev/null || python3 run.py 2>/dev/null || python run.py
