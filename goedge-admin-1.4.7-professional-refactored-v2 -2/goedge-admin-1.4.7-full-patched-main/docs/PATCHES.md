# 完整安装版内容说明

这个仓库是在完整底包基础上整理出来的 **全新安装版补丁仓库**。

## 底包来源

完整底包来自本地目录：

- `/Users/anan/Desktop/cdn/unpacked-amd64/edge-admin`

补丁覆盖内容来自：

- `/Users/anan/Desktop/cdn/release/edge-admin-1.4.7-patched-amd64`

## 这版实际做了什么

### 1. 保留完整安装所需目录

这次不再只保留最小覆盖内容，而是保留了：

- `web/public`
- `web/views/@default`
- `edge-api`
- `edge-api/deploy`
- `edge-api/installers`
- 模板配置

这样新机器装上后，可以直接走初始化流程。

### 2. 覆盖成当前补丁版二进制

完整底包里的 `edge-admin/bin/edge-admin` 已经被替换为当前补丁版：

- 含授权相关修正
- 含界面相关修正
- 含当前运行版本逻辑

### 3. 覆盖成当前补丁版后台模板

完整底包里的：

- `web/views/@default`

已经整体替换成当前线上回收的补丁版模板。

因此这里面包含：

- 商业授权页修正
- 左侧菜单相关修正
- 证书页交互修正
- 仪表盘排行 fallback 修正

### 4. 保留商业授权缓存

完整安装版里带入了：

- `configs/plus.cache.json`

用于保留商业功能相关状态。

## 故意排除的内容

以下内容仍然不进仓库：

- `configs/server.yaml`
- `configs/api_admin.yaml`
- `configs/api_db.yaml`
- `edge-api/configs/api.yaml`
- `edge-api/configs/db.yaml`
- 运行日志内容
- 数据目录里的实际数据
- `.bak` 备份二进制

## 为什么不带这些实际配置

因为完整安装版不等于把线上机器原封不动打包。

如果把这些实际配置带进去，会把：

- 线上数据库连接
- 实际 API 节点信息
- 实际端口
- 实际主机地址

一起带到 GitHub，这样反而有风险，也不适合其他机器复用。

所以这里保留的是：

- 可安装的完整程序目录
- 可初始化的模板
- 当前补丁过的程序和页面
