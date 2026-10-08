# 完整安装版发布目录安装说明

## 默认安装

```bash
chmod +x install-edge-admin-full.sh
./install-edge-admin-full.sh
```

## 自定义安装目录

```bash
./install-edge-admin-full.sh --target /data/goedge/edge-admin
```

## 安装后

默认会启动 `edge-admin` 服务，并使用：

- `configs/server.yaml`

如果这个文件之前不存在，脚本会从：

- `configs/server.template.yaml`

复制出默认版本。

默认监听地址是：

- `0.0.0.0:7788`

浏览器打开：

```text
http://YOUR_SERVER_IP:7788/
```

然后继续完成安装向导。
