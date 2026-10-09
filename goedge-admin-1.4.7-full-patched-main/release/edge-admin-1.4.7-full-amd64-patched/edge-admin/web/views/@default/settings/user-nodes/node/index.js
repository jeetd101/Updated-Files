Tea.context(function () {
	this.success = NotifySuccess("保存成功", "/settings/userNodes/node?nodeId=" + this.node.id)

	this.upgradeNode = function (nodeId,build,version, dlURL) {
        console.log(nodeId,version,dlURL)
		let that = this
		teaweb.confirm("确定要升级此节点吗？", function () {
			that.$post("settings/userNodes/node/upgrade")
				.params({
					nodeId: nodeId,
                    buildVersion: build,
                    latestVersion:version,
                    dlURL: dlURL
				})
				.success(function () {
					teaweb.successRefresh("节点将在后台升级，请稍候刷新查看")
				})
		})
	}
})