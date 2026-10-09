# 其他服务器安装教程

## 1. 前提条件

目标服务器需要满足：

- Linux `x86_64 / amd64`
- 已经安装并能正常运行 `GoEdge Admin 1.4.7`
- 默认安装目录是 `/usr/local/goedge/edge-admin`
- 默认 systemd 服务名是 `edge-admin`

如果你的目录或服务名不一样，安装脚本支持自定义参数。

## 2. 上传发布包

把整个目录打包后上传到目标机，例如：

```bash
tar -czf edge-admin-1.4.7-patched-amd64.tar.gz edge-admin-1.4.7-patched-amd64
scp edge-admin-1.4.7-patched-amd64.tar.gz root@YOUR_SERVER:/root/
```

## 3. 目标机解压

```bash
cd /root
tar -xzf edge-admin-1.4.7-patched-amd64.tar.gz
cd edge-admin-1.4.7-patched-amd64
chmod +x install-edge-admin-patched.sh
```

## 4. 执行安装

### 默认安装

```bash
./install-edge-admin-patched.sh
```

### 自定义安装目录

```bash
./install-edge-admin-patched.sh --target /data/goedge/edge-admin
```

### 自定义服务名

```bash
./install-edge-admin-patched.sh --service edge-admin-custom
```

## 5. 脚本会做什么

脚本只覆盖这几部分：

- `bin/edge-admin`
- `web/views/@default`
- `configs/plus.cache.json`

脚本会自动：

1. 检查架构是不是 amd64
2. 检查目标目录是否存在
3. 备份旧文件到目标目录下的 `.backup-patched-时间戳`
4. 覆盖新二进制和模板
5. 写入无限期 `plus.cache.json`
6. 重启 `edge-admin`
7. 检查服务是否已正常启动

## 6. 安装后验证

### 服务状态

```bash
systemctl status edge-admin --no-pager
```

### 关键验证点

- 后台可以正常登录
- 左侧菜单正常显示
- 系统设置里版本显示 `1.4.7`
- 商业授权页可正常打开
- 证书页面手动续期入口正常
- 首页节点排行/国家地区排行有数据

## 7. 回滚

脚本执行后会输出备份目录，例如：

```bash
/usr/local/goedge/edge-admin/.backup-patched-20260420-130000
```

如果要回滚：

```bash
BACKUP_DIR=/usr/local/goedge/edge-admin/.backup-patched-20260420-130000
TARGET_DIR=/usr/local/goedge/edge-admin

cp -a "$BACKUP_DIR/bin/edge-admin" "$TARGET_DIR/bin/edge-admin"
rm -rf "$TARGET_DIR/web/views/@default"
cp -a "$BACKUP_DIR/web/views/@default" "$TARGET_DIR/web/views/@default"

if [ -f "$BACKUP_DIR/configs/plus.cache.json" ]; then
  cp -a "$BACKUP_DIR/configs/plus.cache.json" "$TARGET_DIR/configs/plus.cache.json"
fi

systemctl restart edge-admin
```

## 8. 备注

- 这个包是 **覆盖安装包**，不是从零部署整套 GoEdge 的初始化包
- 线上数据库、RPC 配置、管理员配置都保留目标机自己的，不会被这个包覆盖
- 如果你后面要传 GitHub，建议一起上传这个目录和打好的 `.tar.gz`
