Tea.context(function () {
	// 打印缩进
	this.indent = function (index) {
		let indent = ""
		for (let i = 0; i < index; i++) {
			indent += " &nbsp; &nbsp; "
		}
		return indent
	}

	this.extractTeaActionData = function (html) {
		if (typeof html != "string" || html.length == 0) {
			return null
		}

		let doc = new DOMParser().parseFromString(html, "text/html")
		let scripts = doc.getElementsByTagName("script")
		for (let i = 0; i < scripts.length; i++) {
			let script = scripts[i].textContent
			if (typeof script != "string" || script.indexOf("window.TEA") < 0) {
				continue
			}

			let match = script.match(/window\.TEA\s*=\s*(\{[\s\S]*\})/)
			if (match == null || match.length < 2) {
				continue
			}

			try {
				let tea = JSON.parse(match[1])
				if (tea != null && tea.ACTION != null && tea.ACTION.data != null) {
					return tea.ACTION.data
				}
			} catch (e) {
				console.error(e)
			}
		}

		return null
	}

	this.findAcmeTask = function (cert, callback) {
		let that = this
		let keyword = cert.taskKeyword
		let url = "/servers/certs/acme"
		if (keyword != null && keyword.length > 0) {
			url += "?keyword=" + window.encodeURIComponent(keyword)
		}

		axios.get(url, {
			headers: {
				"X-Requested-With": "XMLHttpRequest"
			}
		}).then(function (resp) {
			let data = that.extractTeaActionData(resp.data)
			if (data == null || !Array.isArray(data.tasks)) {
				callback(null)
				return
			}

			let task = null
			data.tasks.some(function (item) {
				if (item != null && item.cert != null && item.cert.id == cert.id) {
					task = item
					return true
				}
				return false
			})

			if (task == null && cert != null && cert.dnsNames != null && cert.dnsNames.length > 0) {
				data.tasks.some(function (item) {
					if (item == null || item.domains == null || item.domains.length == 0) {
						return false
					}

					return item.domains.some(function (domain) {
						if (cert.dnsNames.indexOf(domain) >= 0) {
							task = item
							return true
						}
						return false
					})
				})
			}

			callback(task)
		}).catch(function () {
			callback(null)
		})
	}

	this.renewCert = function (cert) {
		let that = this
		if (cert == null) {
			return
		}

		teaweb.confirm("html:确定要立即续期此证书吗？<br/>系统会执行关联的ACME任务。", function () {
			that.findAcmeTask(cert, function (task) {
				if (task == null || task.id == null || task.id <= 0) {
					teaweb.warn("未找到关联的ACME任务，已为你打开任务列表。", function () {
						that.viewAcmeTasks(cert)
					})
					return
				}

				Tea.action("/servers/certs/acme/run")
					.params({
						taskId: task.id
					})
					.timeout(300)
					.success(function (resp) {
					let renewedCertId = resp.data.certId
					teaweb.success("续期任务执行成功", function () {
						if (renewedCertId > 0 && renewedCertId != cert.id) {
							window.location = "/servers/certs/certPopup?certId=" + renewedCertId
							return
						}
						window.location.reload()
					})
					})
					.fail(function (resp) {
						let message = "续期任务执行失败，已为你打开关联任务页。"
						if (resp != null && resp.message != null && resp.message.length > 0) {
							message = resp.message
						}
						teaweb.warn(message, function () {
							that.viewAcmeTasks(cert)
						})
					})
					.post()
			})
		})
	}

	this.viewAcmeTasks = function (info) {
		let keyword = info.taskKeyword
		let url = "/servers/certs/acme"
		if (keyword != null && keyword.length > 0) {
			url += "?keyword=" + window.encodeURIComponent(keyword)
		}
		window.open(url, "_blank")
	}
})
