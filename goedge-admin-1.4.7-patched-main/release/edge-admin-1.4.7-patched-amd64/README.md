# edge-admin-1.4.7-patched-amd64

这是从当前线上机器 `162.120.71.174` 回收下来的 **Edge Admin 1.4.7 amd64 补丁发布目录**。

这个目录不是全新初始化包，而是给 **已经安装过 GoEdge Admin 1.4.7 amd64** 的服务器做覆盖升级用。

## 包含内容

- `bin/edge-admin`：当前线上正在使用的补丁二进制
- `web/views/@default`：当前线上正在使用的后台模板
- `configs/plus.cache.json`：无限期商业版缓存
- `install-edge-admin-patched.sh`：一键安装脚本
- `INSTALL.md`：其他服务器安装教程
- `BUILD-INFO.txt`：来源、校验值、打包信息

## 不包含内容

这些是运行时配置/数据，避免把线上敏感信息带进 GitHub，所以没有打进发布目录：

- `configs/server.yaml`
- `configs/api_admin.yaml`
- `configs/api_db.yaml`
- `edge-api/**`
- `data/**`
- `logs/**`

## 适用场景

- 目标机已经有 `edge-admin` 服务
- 目标机目录默认为 `/usr/local/goedge/edge-admin`
- 目标机架构是 `x86_64 / amd64`

## 快速安装

```bash
cd edge-admin-1.4.7-patched-amd64
chmod +x install-edge-admin-patched.sh
sudo ./install-edge-admin-patched.sh
```

完整步骤见 `INSTALL.md`。
