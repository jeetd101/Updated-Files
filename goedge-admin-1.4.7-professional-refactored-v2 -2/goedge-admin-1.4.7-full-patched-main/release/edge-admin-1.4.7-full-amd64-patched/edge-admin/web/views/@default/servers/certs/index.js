Tea.context(function () {
	this.certIds = []
	this.allChecked = false
	this.isDeletingSelected = false
	this.renewingCertId = 0

	this.certs.forEach(function (cert) {
		cert.isChecked = false
	})

	this.certKeyword = function (cert) {
		if (cert != null && cert.dnsNames != null && cert.dnsNames.length > 0) {
			return cert.dnsNames[0]
		}
		if (cert != null && cert.name != null) {
			return cert.name
		}
		return ""
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
		let keyword = this.certKeyword(cert)
		let url = "/servers/certs/acme"
		if (keyword.length > 0) {
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

	this.runAcmeTask = function (cert, taskId) {
		let that = this
		Tea.action("/servers/certs/acme/run")
			.params({
				taskId: taskId
			})
			.timeout(300)
			.success(function () {
				teaweb.success("续期任务执行成功", function () {
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
			.done(function () {
				that.renewingCertId = 0
			})
			.post()
	}

	this.deleteCertsSequentially = function (certIds, index) {
		let that = this
		if (index >= certIds.length) {
			this.isDeletingSelected = false
			teaweb.success("删除成功", function () {
				window.location.reload()
			})
			return
		}

		Tea.action("/servers/certs/delete")
			.params({
				certId: certIds[index]
			})
			.success(function () {
				that.deleteCertsSequentially(certIds, index + 1)
			})
			.fail(function (resp) {
				that.isDeletingSelected = false
				let message = "删除失败，请稍后重试。"
				if (resp != null && resp.message != null && resp.message.length > 0) {
					message = resp.message
				}
				teaweb.warn(message)
			})
			.post()
	}

	// 上传证书
	this.uploadCert = function () {
		teaweb.popup("/servers/certs/uploadPopup?userId=" + this.searchingUserId, {
			height: "30em",
			callback: function () {
				teaweb.success("上传成功", function () {
					window.location.reload()
				})
			}
		})
	}

	// 批量上传证书
	this.uploadBatch = function () {
		teaweb.popup("/servers/certs/uploadBatchPopup?userId=" + this.searchingUserId, {
			callback: function () {
				window.location.reload()
			}
		})
	}

	this.changeAllCerts = function (b) {
		this.certs.forEach(function (cert) {
			cert.isChecked = b
		})
		this.changeCerts()
	}

	this.changeCerts = function () {
		if (this.certs.length == 0) {
			this.certIds = []
			this.allChecked = false
			return
		}

		let certIds = []
		this.certs.forEach(function (cert) {
			if (cert.isChecked) {
				certIds.push(cert.id)
			}
		})
		this.certIds = certIds
		this.allChecked = certIds.length == this.certs.length
	}

	this.deleteCerts = function (certIds, tip) {
		let that = this
		if (certIds == null || certIds.length == 0) {
			return
		}

		teaweb.confirm(tip, function () {
			that.isDeletingSelected = certIds.length > 1
			that.deleteCertsSequentially(certIds.slice(0), 0)
		})
	}

	// 删除证书
	this.deleteCert = function (certId) {
		this.deleteCerts([certId], "确定要删除此证书吗？")
	}

	this.deleteSelectedCerts = function () {
		if (this.certIds.length == 0 || this.isDeletingSelected) {
			return
		}
		this.deleteCerts(this.certIds, "确定要删除选中的 " + this.certIds.length + " 个证书吗？")
	}

	// 立即续期
	this.renewCert = function (cert) {
		let that = this
		if (cert == null || this.renewingCertId > 0) {
			return
		}

		teaweb.confirm("html:确定要立即续期此证书吗？<br/>系统会执行关联的ACME任务。", function () {
			that.renewingCertId = cert.id
			that.findAcmeTask(cert, function (task) {
				if (task == null || task.id == null || task.id <= 0) {
					that.renewingCertId = 0
					teaweb.warn("未找到关联的ACME任务，已为你打开任务列表。", function () {
						that.viewAcmeTasks(cert)
					})
					return
				}

				that.runAcmeTask(cert, task.id)
			})
		})
	}

	this.viewAcmeTasks = function (cert) {
		let keyword = this.certKeyword(cert)
		let url = "/servers/certs/acme"
		if (keyword != null && keyword.length > 0) {
			url += "?keyword=" + window.encodeURIComponent(keyword)
		}
		window.open(url, "_blank")
	}

	// 查看证书
	this.viewCert = function (certId) {
		teaweb.popup("/servers/certs/certPopup?certId=" + certId, {
			height: "28em",
			width: "48em"
		})
	}

	// 修改证书
	this.updateCert = function (certId) {
		teaweb.popup("/servers/certs/updatePopup?certId=" + certId, {
			height: "30em",
			callback: function () {
				teaweb.success("修改成功", function () {
					window.location.reload()
				})
			}
		})
	}
})
