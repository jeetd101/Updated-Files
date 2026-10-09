# GoEdge Admin 1.4.7 Full Install Patched

这是一个适合直接上传 GitHub 的 **完整安装版** 仓库。

它和之前的覆盖升级版不同，这个仓库带了：

- `edge-admin` 主程序
- `web/public`
- `web/views/@default`
- `edge-api`
- 节点部署压缩包
- 安装辅助程序
- 模板配置

用途是给 **全新机器首次安装** `GoEdge Admin 1.4.7 amd64`，同时保留当前补丁版的二进制、前端模板和商业授权缓存。

## 为什么会有两个 1.4.7 仓库

现在有两个仓库，作用不一样：

- `goedge-admin-1.4.7-full-patched`：**完整安装版**，给 **新机器首次安装**
- `goedge-admin-1.4.7-patched`：**覆盖升级版**，给 **已经安装好 1.4.7** 的机器替换补丁

如果你是新机器，直接用当前这个仓库。

如果你只是给现有 1.4.7 机器打补丁，用另一个仓库：

- [https://github.com/jiasu9527/goedge-admin-1.4.7-patched](https://github.com/jiasu9527/goedge-admin-1.4.7-patched)

## 一键安装命令

适用场景：

- 新机器首次安装
- 想直接从 GitHub Release 下载完整安装包

命令：

```bash
curl -fsSL -o /tmp/edge-admin-1.4.7-full-amd64-patched.tar.gz https://github.com/jiasu9527/goedge-admin-1.4.7-full-patched/releases/download/v1.4.7-full-patched/edge-admin-1.4.7-full-amd64-patched.tar.gz && cd /tmp && rm -rf edge-admin-1.4.7-full-amd64-patched && tar -xzf edge-admin-1.4.7-full-amd64-patched.tar.gz && cd edge-admin-1.4.7-full-amd64-patched && chmod +x install-edge-admin-full.sh && sudo ./install-edge-admin-full.sh
```

## 目录结构

- `release/edge-admin-1.4.7-full-amd64-patched/`：完整安装发布目录
- `scripts/make-dist.sh`：生成可分发压缩包和 `SHA256SUMS`
- `docs/INSTALL.md`：完整安装教程
- `docs/PATCHES.md`：完整安装版里包含了什么
- `dist/`：打包生成物，默认不提交

## 这个仓库包含什么

发布目录里的核心结构是：

- `edge-admin/bin/edge-admin`
- `edge-admin/configs/server.template.yaml`
- `edge-admin/configs/plus.cache.json`
- `edge-admin/web/public`
- `edge-admin/web/views/@default`
- `edge-admin/edge-api/bin/edge-api`
- `edge-admin/edge-api/configs/api.template.yaml`
- `edge-admin/edge-api/configs/db.template.yaml`
- `edge-admin/edge-api/deploy/*`
- `edge-admin/edge-api/installers/*`
- `install-edge-admin-full.sh`

## 故意不带的东西

这个仓库是完整安装底包，但依然 **不带线上实际私密配置和运行数据**：

- `configs/server.yaml`
- `configs/api_admin.yaml`
- `configs/api_db.yaml`
- `edge-api/configs/api.yaml`
- `edge-api/configs/db.yaml`
- 实际数据库内容
- 日志内容
- 线上备份文件

这些会在安装后由你在 Web 安装向导里初始化生成，或者由系统运行时自己创建。

## 适用范围

- Linux
- `x86_64 / amd64`
- 全新机器首次安装
- 也可以给已有同版本机器做整体替换，但重点场景是新装

## 快速打包

```bash
cd /Users/anan/Desktop/cdn/github/goedge-admin-1.4.7-full-patched
chmod +x scripts/make-dist.sh
./scripts/make-dist.sh
```

打包后会生成：

- `dist/edge-admin-1.4.7-full-amd64-patched.tar.gz`
- `dist/SHA256SUMS`

## 完整安装流程

完整步骤见：

- `/Users/anan/Desktop/cdn/github/goedge-admin-1.4.7-full-patched/docs/INSTALL.md`

## 补丁说明

见：

- `/Users/anan/Desktop/cdn/github/goedge-admin-1.4.7-full-patched/docs/PATCHES.md`
