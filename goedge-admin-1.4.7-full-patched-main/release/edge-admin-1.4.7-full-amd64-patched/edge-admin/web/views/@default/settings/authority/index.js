Tea.context(function () {
	this.success = NotifyReloadSuccess("申请试用成功")

	if (this.teaIsPlus && this.key == null) {
		let updatedTime = new Date().toLocaleString()
		this.key = {
			editionName: "Enterprise Unlimited",
			company: "Local Unlimited License",
			dayFrom: "2026-04-20",
			dayTo: "终身授权",
			nodes: 0,
			components: [],
			method: "offline",
			updatedTime: updatedTime,
			isExpired: false,
			isExpiring: false
		}

		if (this.quota == null) {
			this.quota = {
				countNodes: 0,
				maxNodes: 0
			}
		}
	}
})
