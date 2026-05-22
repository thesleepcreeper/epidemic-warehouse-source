# 大理州动物防疫物资管理软件

![打包发布](https://github.com/thesleepcreeper/epidemic-warehouse-source/actions/workflows/build.yml/badge.svg)
![最新下载](https://img.shields.io/github/v/release/thesleepcreeper/epidemic-warehouse-source)

## 功能

- 物资管理（实物储备 + 协议储备）
- 出入库管理（入库/出库/审批）
- 库存预警（低库存+临期预警）
- 统计报表 + 储备总览
- 用户权限（管理员/普通用户/只读）
- 单机离线运行，解压即用

## 下载

👉 [**点此下载最新版**](https://github.com/thesleepcreeper/epidemic-warehouse-source/releases/latest)

| 平台 | 下载文件 | 说明 |
|------|---------|------|
| Linux x86_64 | `epidemic-warehouse-linux-x86_64.tar.gz` | Ubuntu / CentOS / 统信等 |
| macOS ARM64 | `epidemic-warehouse-macos-arm64.tar.gz` | Apple Silicon (M1/M2/M3) |

## 启动方式

Linux/macOS:
```bash
tar xzf epidemic-warehouse-*.tar.gz
cd epidemic-warehouse
./启动.sh
```

Windows:
```bash
# 暂不支持自动打包，需手动构建
```

## Web模式（局域网访问）

```bash
./启动.sh --web
# 然后同局域网其他设备访问 http://<本机IP>:5001
```

## 默认账号

- 管理员: admin / admin123
- 普通用户: user / user123

## 技术栈

Flask + SQLite + pywebview + PyInstaller
