Tea.context(function () {
	this.success = NotifyReloadSuccess("保存成功")
    this.deleteStorage = function (id) {
		let that = this
		teaweb.confirm("确定要删除这个存储吗？", function () {
			that.$post("/settings/pages/storages/delete")
				.params({
					id: id
				})
				.success(function () {
					teaweb.success("删除成功", function () {
						teaweb.reload()
					})
				})
		})
	}
})