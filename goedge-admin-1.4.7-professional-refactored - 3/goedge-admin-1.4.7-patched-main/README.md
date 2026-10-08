# GoEdge Admin 1.4.7 Patched

这是一个适合直接上传到 GitHub 的补丁发布仓库，用来分发当前线上回收下来的 `GoEdge Admin 1.4.7 amd64` 已修补版本。

这个仓库提供的是 **覆盖升级包**，不是全新安装包。目标机需要已经安装过 `GoEdge Admin 1.4.7`。

## 为什么会有两个 1.4.7 仓库

现在有两个仓库，作用不一样：

- `goedge-admin-1.4.7-patched`：**覆盖升级版**，给 **已经安装好 1.4.7** 的机器直接替换补丁
- `goedge-admin-1.4.7-full-patched`：**完整安装版**，给 **新机器首次安装**

如果你的机器本来就已经在跑 `GoEdge Admin 1.4.7`，用当前这个仓库。

如果你的机器是新装，直接用完整安装版：

- [https://github.com/jiasu9527/goedge-admin-1.4.7-full-patched](https://github.com/jiasu9527/goedge-admin-1.4.7-full-patched)

## 一键安装命令

适用场景：

- 机器里已经装好了 `GoEdge Admin 1.4.7`
- 你只想覆盖成补丁版

命令：

```bash
curl -fsSL -o /tmp/edge-admin-1.4.7-patched-amd64.tar.gz https://github.com/jiasu9527/goedge-admin-1.4.7-patched/releases/download/v1.4.7-patched/edge-admin-1.4.7-patched-amd64.tar.gz && cd /tmp && rm -rf edge-admin-1.4.7-patched-amd64 && tar -xzf edge-admin-1.4.7-patched-amd64.tar.gz && cd edge-admin-1.4.7-patched-amd64 && chmod +x install-edge-admin-patched.sh && sudo ./install-edge-admin-patched.sh
```

## 目录结构

- `release/edge-admin-1.4.7-patched-amd64/`：实际发布目录
- `scripts/make-dist.sh`：生成可分发 `.tar.gz` 和 `SHA256SUMS`
- `docs/INSTALL.md`：其他服务器安装教程
- `docs/PATCHES.md`：这次补丁内容说明
- `dist/`：打包生成物，默认不提交

## 发布目录包含内容

- `bin/edge-admin`
- `web/views/@default`
- `configs/plus.cache.json`
- `install-edge-admin-patched.sh`

## 明确不包含

以下内容属于线上敏感配置或运行数据，没有被带入仓库：

- `configs/server.yaml`
- `configs/api_admin.yaml`
- `configs/api_db.yaml`
- `edge-api/**`
- `data/**`
- `logs/**`

## 适用范围

- 目标机系统：Linux
- 目标机架构：`x86_64 / amd64`
- 目标机版本基线：`GoEdge Admin 1.4.7`
- 默认安装目录：`/usr/local/goedge/edge-admin`
- 默认服务名：`edge-admin`

## 快速打包

```bash
cd github/goedge-admin-1.4.7-patched
chmod +x scripts/make-dist.sh
./scripts/make-dist.sh
```

打包后生成：

- `dist/edge-admin-1.4.7-patched-amd64.tar.gz`
- `dist/SHA256SUMS`

## 上传到 GitHub 建议

建议提交仓库目录本身，不要提交 `dist/` 里的生成物；生成物可以放到 GitHub Release 附件。

典型流程：

```bash
cd github/goedge-admin-1.4.7-patched
git init
git add .
git commit -m "chore: add edge-admin 1.4.7 patched release repo"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

然后执行一次：

```bash
./scripts/make-dist.sh
```

把 `dist/edge-admin-1.4.7-patched-amd64.tar.gz` 和 `dist/SHA256SUMS` 上传到 GitHub Release 即可。

## 安装说明

服务器安装步骤见：

- `/Users/anan/Desktop/cdn/github/goedge-admin-1.4.7-patched/docs/INSTALL.md`

## 补丁内容

补丁说明见：

- `/Users/anan/Desktop/cdn/github/goedge-admin-1.4.7-patched/docs/PATCHES.md`
