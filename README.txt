# 大理州动物防疫物资管理软件 v2.0

## 特点
- 独立桌面窗口，不依赖浏览器
- 无需安装 Python，解压即用
- 数据保存在本地 SQLite，安全可靠

## 系统要求

**Windows / Linux / macOS**: 仅需操作系统本身，无需 Python

## 启动方式

### macOS 打包版
解压后直接双击 `大理州动物防疫物资管理软件` 即可启动独立窗口。

### Windows / Linux
在 Windows/Linux 上需要用 PyInstaller 重新编译：
```bash
pip install pyinstaller pywebview
cd 项目目录
pyinstaller build.spec
```
编译后在 `dist/` 目录生成可执行文件。

## 默认登录账号
- 管理员: admin
- 密码: admin123

## 数据存储
所有数据保存在程序同目录的 `data/warehouse.db` 文件中。
删除 `data/` 目录可重置系统。

## 功能一览
- 物资管理（分类、供应商、物资CRUD）
- 出入库管理（含审批流程）
- 库存预警 + 临期预警（默认90天）
- 批量导入/导出 Excel
- 年度结转
- 打印报表（含单位名称）
- 单位名称自定义设置
- 用户权限管理（管理员/仓管员/操作员）

## 端口说明
如果 5000 端口被占用，启动时自动使用环境变量 PORT 指定的端口。
Windows: `set PORT=5001` 后再启动
Linux/Mac: `PORT=5001 ./大理州动物防疫物资管理软件`
