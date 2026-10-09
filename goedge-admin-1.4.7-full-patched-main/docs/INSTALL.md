# 完整安装说明

这个仓库发布的是 `edge-admin-1.4.7-full-amd64-patched`，适合 **新机器首次安装**。

## 先看你该用哪个仓库

- **新机器首次安装**：用当前仓库 `goedge-admin-1.4.7-full-patched`
- **已安装 1.4.7 的机器只打补丁**：用 `goedge-admin-1.4.7-patched`

覆盖升级仓库地址：

- [https://github.com/jiasu9527/goedge-admin-1.4.7-patched](https://github.com/jiasu9527/goedge-admin-1.4.7-patched)

## 一键安装命令

适用于新机器首次安装：

```bash
curl -fsSL -o /tmp/edge-admin-1.4.7-full-amd64-patched.tar.gz https://github.com/jiasu9527/goedge-admin-1.4.7-full-patched/releases/download/v1.4.7-full-patched/edge-admin-1.4.7-full-amd64-patched.tar.gz && cd /tmp && rm -rf edge-admin-1.4.7-full-amd64-patched && tar -xzf edge-admin-1.4.7-full-amd64-patched.tar.gz && cd edge-admin-1.4.7-full-amd64-patched && chmod +x install-edge-admin-full.sh && sudo ./install-edge-admin-full.sh
```

## 1. 前提

- Linux `x86_64 / amd64`
- 目标机有 `systemd`
- 目标机能访问 MySQL，或者你准备在安装向导里自动安装 / 手工配置 MySQL

## 2. 本地生成发布包

```bash
cd /Users/anan/Desktop/cdn/github/goedge-admin-1.4.7-full-patched
chmod +x scripts/make-dist.sh
./scripts/make-dist.sh
```

生成物：

- `dist/edge-admin-1.4.7-full-amd64-patched.tar.gz`
- `dist/SHA256SUMS`

## 3. 上传到服务器

```bash
scp dist/edge-admin-1.4.7-full-amd64-patched.tar.gz root@YOUR_SERVER:/root/
scp dist/SHA256SUMS root@YOUR_SERVER:/root/
```

可选校验：

```bash
cd /root
sha256sum -c SHA256SUMS
```

## 4. 解压并执行安装

```bash
cd /root
tar -xzf edge-admin-1.4.7-full-amd64-patched.tar.gz
cd edge-admin-1.4.7-full-amd64-patched
chmod +x install-edge-admin-full.sh
./install-edge-admin-full.sh
```

如果你要装到其他目录：

```bash
./install-edge-admin-full.sh --target /data/goedge/edge-admin
```

## 5. 安装脚本会做什么

脚本会：

1. 把完整 `edge-admin/` 目录复制到目标目录
2. 写入 patched 二进制和 patched 模板
3. 写入 `plus.cache.json`
4. 首次安装时把 `configs/server.template.yaml` 复制成 `configs/server.yaml`
5. 创建 `edge-admin` 的 systemd 服务
6. 启动 `edge-admin`

## 6. 安装后初始化

安装脚本跑完后，默认监听端口来自：

- `edge-admin/configs/server.yaml`

默认模板里是：

- `0.0.0.0:7788`

所以你通常可以打开：

```text
http://YOUR_SERVER_IP:7788/
```

首次进入会进入安装向导，顺序大致是：

1. 设置 API 节点
2. 设置 MySQL 数据库
3. 设置管理员账号
4. 完成初始化

## 7. 哪些配置是安装后生成的

这个包不会直接带这些实际运行配置：

- `configs/api_admin.yaml`
- `configs/api_db.yaml`
- `edge-api/configs/api.yaml`
- `edge-api/configs/db.yaml`

原因很简单：这些配置和每台机器自己的数据库、端口、节点信息强相关。

它们会在你完成 Web 初始化时由系统生成。

## 8. 安装后核对

至少检查：

- `systemctl status edge-admin --no-pager`
- 页面能打开
- 首次安装向导能正常进入
- 完成初始化后可以登录后台
- 设置里版本显示 `1.4.7`
- 商业授权页可以打开

## 9. 回滚

脚本执行时如果目标目录原来已经有内容，会先在目标目录里做备份：

```text
.backup-full-时间戳
```

回滚方式：

1. 停掉 `edge-admin`
2. 把备份目录内容恢复到目标目录
3. 再启动服务

## 10. 说明

- 这是 **完整安装仓库**
- 不是最小覆盖补丁包
- 重点是让新机器能直接装起来，再通过安装向导生成本机配置
