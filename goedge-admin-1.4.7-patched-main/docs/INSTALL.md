# 安装说明

这个仓库发布的是 `edge-admin-1.4.7-patched-amd64` 覆盖安装包。

## 先看你该用哪个仓库

- **已安装 1.4.7 的机器**：用当前仓库 `goedge-admin-1.4.7-patched`
- **新机器首次安装**：用完整安装仓库 `goedge-admin-1.4.7-full-patched`

完整安装仓库地址：

- [https://github.com/jiasu9527/goedge-admin-1.4.7-full-patched](https://github.com/jiasu9527/goedge-admin-1.4.7-full-patched)

## 一键安装命令

适用于已经安装好 `GoEdge Admin 1.4.7` 的服务器，直接覆盖升级：

```bash
curl -fsSL -o /tmp/edge-admin-1.4.7-patched-amd64.tar.gz https://github.com/jiasu9527/goedge-admin-1.4.7-patched/releases/download/v1.4.7-patched/edge-admin-1.4.7-patched-amd64.tar.gz && cd /tmp && rm -rf edge-admin-1.4.7-patched-amd64 && tar -xzf edge-admin-1.4.7-patched-amd64.tar.gz && cd edge-admin-1.4.7-patched-amd64 && chmod +x install-edge-admin-patched.sh && sudo ./install-edge-admin-patched.sh
```

## 前提条件

目标服务器需要满足：

- Linux `x86_64 / amd64`
- 已经安装并运行 `GoEdge Admin 1.4.7`
- 默认目录是 `/usr/local/goedge/edge-admin`
- 默认 systemd 服务名是 `edge-admin`

如果你的目录或服务名不一样，安装脚本支持自定义参数。

## 生成发布包

在仓库根目录执行：

```bash
chmod +x scripts/make-dist.sh
./scripts/make-dist.sh
```

生成结果：

- `dist/edge-admin-1.4.7-patched-amd64.tar.gz`
- `dist/SHA256SUMS`

## 上传到目标机

```bash
scp dist/edge-admin-1.4.7-patched-amd64.tar.gz root@YOUR_SERVER:/root/
scp dist/SHA256SUMS root@YOUR_SERVER:/root/
```

可选校验：

```bash
cd /root
sha256sum -c SHA256SUMS
```

## 目标机安装

```bash
cd /root
tar -xzf edge-admin-1.4.7-patched-amd64.tar.gz
cd edge-admin-1.4.7-patched-amd64
chmod +x install-edge-admin-patched.sh
./install-edge-admin-patched.sh
```

## 自定义参数

自定义安装目录：

```bash
./install-edge-admin-patched.sh --target /data/goedge/edge-admin
```

自定义服务名：

```bash
./install-edge-admin-patched.sh --service edge-admin-custom
```

## 安装脚本会做什么

脚本只会覆盖这些内容：

- `bin/edge-admin`
- `web/views/@default`
- `configs/plus.cache.json`

脚本会自动：

1. 校验架构是否为 `amd64`
2. 检查目标目录存在
3. 备份旧文件到 `.backup-patched-时间戳`
4. 覆盖二进制和模板
5. 写入 `plus.cache.json`
6. 重启 `edge-admin`
7. 检查服务是否成功启动

## 安装后核对

建议至少检查：

- 后台能正常登录
- 左侧菜单正常显示
- 设置里版本显示 `1.4.7`
- 商业授权页能打开
- 证书页面操作正常
- 首页节点排行/国家地区排行有数据

## 回滚

安装脚本执行后会输出备份目录，回滚时把备份的：

- `bin/edge-admin`
- `web/views/@default`
- `configs/plus.cache.json`

恢复回目标目录后，再执行：

```bash
systemctl restart edge-admin
```
