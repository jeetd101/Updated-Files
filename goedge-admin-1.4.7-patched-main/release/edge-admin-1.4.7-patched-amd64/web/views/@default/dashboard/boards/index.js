function dashboardParseTeaActionDataFromHTML(html) {
	if (typeof (html) != "string" || html.length == 0) {
		return null
	}

	let scriptIndex = html.indexOf("window.TEA")
	if (scriptIndex < 0) {
		return null
	}

	let scriptEnd = html.indexOf("</script>", scriptIndex)
	if (scriptEnd < 0) {
		return null
	}

	let scriptBody = html.substring(scriptIndex, scriptEnd)
	let sandboxWindow = {}
	let tea = (new Function("window", scriptBody + "; return window.TEA || null;"))(sandboxWindow)
	if (tea == null || tea.ACTION == null) {
		return null
	}

	return tea.ACTION.data || null
}

function dashboardExtractMaxPage(pageHTML) {
	if (typeof (pageHTML) != "string" || pageHTML.length == 0) {
		return 1
	}

	let matches = pageHTML.match(/page=(\d+)/g)
	if (!Array.isArray(matches) || matches.length == 0) {
		return 1
	}

	let maxPage = 1
	matches.forEach(function (match) {
		let pieces = match.split("=")
		let page = parseInt(pieces[1], 10)
		if (!isNaN(page) && page > maxPage) {
			maxPage = page
		}
	})
	return maxPage
}

function dashboardMergeTopNodeStats(boardDataList) {
	let statsMap = {}
	if (!Array.isArray(boardDataList)) {
		return []
	}

	boardDataList.forEach(function (boardData) {
		if (boardData == null || !Array.isArray(boardData.topNodeStats)) {
			return
		}

		boardData.topNodeStats.forEach(function (stat) {
			if (stat == null) {
				return
			}

			let nodeId = parseInt(stat.nodeId, 10)
			if (isNaN(nodeId) || nodeId <= 0) {
				return
			}

			if (statsMap[nodeId] == null) {
				statsMap[nodeId] = {
					nodeId: nodeId,
					nodeName: stat.nodeName || ("节点#" + nodeId),
					countRequests: 0,
					bytes: 0
				}
			}

			statsMap[nodeId].countRequests += parseInt(stat.countRequests, 10) || 0
			statsMap[nodeId].bytes += parseInt(stat.bytes, 10) || 0
			if ((statsMap[nodeId].nodeName == null || statsMap[nodeId].nodeName.length == 0) && typeof (stat.nodeName) == "string" && stat.nodeName.length > 0) {
				statsMap[nodeId].nodeName = stat.nodeName
			}
		})
	})

	return Object.values(statsMap)
		.sort(function (a, b) {
			if (b.countRequests != a.countRequests) {
				return b.countRequests - a.countRequests
			}
			return b.bytes - a.bytes
		})
		.slice(0, 10)
}

function dashboardFormatPercent(value) {
	let percent = Math.round(value * 100) / 100
	let percentString = percent.toFixed(2)
	percentString = percentString.replace(/\.00$/, "")
	percentString = percentString.replace(/(\.\d)0$/, "$1")
	return percentString
}

function dashboardBuildFallbackCountryStats(regionPageDataList, formatCount) {
	let statsMap = {}
	let totalCount = 0
	if (typeof (formatCount) != "function") {
		formatCount = function (count) {
			return String(count)
		}
	}

	if (!Array.isArray(regionPageDataList)) {
		return []
	}

	regionPageDataList.forEach(function (pageData) {
		if (pageData == null || !Array.isArray(pageData.countryStats)) {
			return
		}

		pageData.countryStats.forEach(function (stat) {
			if (stat == null || stat.country == null) {
				return
			}

			let countryId = parseInt(stat.country.id, 10)
			if (isNaN(countryId) || countryId <= 0) {
				return
			}

			if (statsMap[countryId] == null) {
				statsMap[countryId] = {
					countryId: countryId,
					name: stat.country.name || ("地区#" + countryId),
					countRequests: 0
				}
			}

			let count = parseInt(stat.count, 10) || 0
			statsMap[countryId].countRequests += count
			totalCount += count
		})
	})

	return Object.values(statsMap)
		.sort(function (a, b) {
			return b.countRequests - a.countRequests
		})
		.slice(0, 10)
		.map(function (stat) {
			let percent = 0
			if (totalCount > 0) {
				percent = stat.countRequests * 100 / totalCount
			}

			return {
				countryId: stat.countryId,
				name: stat.name,
				bytes: stat.countRequests,
				countRequests: stat.countRequests,
				countAttackRequests: 0,
				formattedBytes: formatCount(stat.countRequests),
				percent: dashboardFormatPercent(percent)
			}
		})
}

if (typeof (Tea) != "undefined" && Tea.context != null) {
Tea.context(function () {
	this.isLoading = true
	this.trafficTab = "hourly"
	this.metricCharts = []
	this.plusExpireDay = ""
	this.topCountryStats = []
	this.topCountryStatsKey = 0
	this.yesterdayPercentFormat = ""
	this.localLowerVersionAPINode = null
	this.countWeakAdmins = 0
	this.todayCountIPsFormat = "0"
	this.isLoadingFallbackStats = false
	this.isTopNodeFallback = false
	this.isTopCountryFallback = false

	this.nodeValuesStat = null

	this.dashboardFallbackCacheKey = function () {
		return "dashboard.boards.fallback.v1"
	}

	this.loadDashboardFallbackCache = function () {
		try {
			let value = sessionStorage.getItem(this.dashboardFallbackCacheKey())
			if (value == null || value.length == 0) {
				return null
			}

			let cache = JSON.parse(value)
			if (cache == null || typeof (cache) != "object") {
				return null
			}
			if (typeof (cache.expiredAt) != "number" || cache.expiredAt < Date.now()) {
				sessionStorage.removeItem(this.dashboardFallbackCacheKey())
				return null
			}

			return cache.dataPackage || null
		} catch (e) {
			return null
		}
	}

	this.saveDashboardFallbackCache = function (dataPackage) {
		try {
			sessionStorage.setItem(this.dashboardFallbackCacheKey(), JSON.stringify({
				expiredAt: Date.now() + 10 * 60 * 1000,
				dataPackage: dataPackage
			}))
		} catch (e) {
		}
	}

	this.fetchDashboardHTMLData = async function (url) {
		let response = await fetch(url, {
			credentials: "same-origin",
			cache: "no-store"
		})
		if (!response.ok) {
			throw new Error("request failed: " + url + " " + response.status)
		}

		let html = await response.text()
		return dashboardParseTeaActionDataFromHTML(html)
	}

	this.postDashboardJSON = function (url, params) {
		let that = this
		return new Promise(function (resolve, reject) {
			let request = that.$post(url)
			if (params != null) {
				request.params(params)
			}

			request
				.success(function (resp) {
					resolve(resp.data)
				})
				.error(function (resp) {
					reject(resp)
				})
		})
	}

	this.mapInBatches = async function (items, limit, callback) {
		let results = []
		for (let i = 0; i < items.length; i += limit) {
			let chunk = items.slice(i, i + limit)
			let chunkResults = await Promise.all(chunk.map(callback))
			results = results.concat(chunkResults)
		}
		return results
	}

	this.fetchTopNodeStatsFallback = async function () {
		let clusterPageData = await this.fetchDashboardHTMLData("/clusters")
		if (clusterPageData == null || !Array.isArray(clusterPageData.clusters)) {
			return []
		}

		let clusterIds = []
		clusterPageData.clusters.forEach(function (cluster) {
			if (cluster == null) {
				return
			}

			let clusterId = parseInt(cluster.id, 10)
			if (!isNaN(clusterId) && clusterId > 0 && !clusterIds.includes(clusterId)) {
				clusterIds.push(clusterId)
			}
		})

		let boardDataList = await Promise.all(clusterIds.map((clusterId) => {
			return this.postDashboardJSON("/clusters/cluster/boards", {
				clusterId: clusterId
			}).catch(function () {
				return null
			})
		}))
		return dashboardMergeTopNodeStats(boardDataList)
	}

	this.fetchTopCountryStatsFallback = async function () {
		let that = this
		let firstServerPageData = await this.fetchDashboardHTMLData("/servers")
		if (firstServerPageData == null) {
			return []
		}

		let pageNumbers = []
		let maxPage = dashboardExtractMaxPage(firstServerPageData.page)
		for (let page = 2; page <= maxPage; page++) {
			pageNumbers.push(page)
		}

		let serverPageDataList = [firstServerPageData]
		if (pageNumbers.length > 0) {
			let extraServerPages = await this.mapInBatches(pageNumbers, 2, async function (page) {
				return await that.fetchDashboardHTMLData("/servers?page=" + page).catch(function () {
					return null
				})
			})
			serverPageDataList = serverPageDataList.concat(extraServerPages)
		}

		let serverIdMap = {}
		serverPageDataList.forEach(function (pageData) {
			if (pageData == null || !Array.isArray(pageData.servers)) {
				return
			}

			pageData.servers.forEach(function (server) {
				if (server == null) {
					return
				}

				let serverId = parseInt(server.id, 10)
				if (!isNaN(serverId) && serverId > 0) {
					serverIdMap[serverId] = true
				}
			})
		})

		let serverIds = Object.keys(serverIdMap).map(function (serverId) {
			return parseInt(serverId, 10)
		})
		let regionPageDataList = await this.mapInBatches(serverIds, 4, async function (serverId) {
			return await that.fetchDashboardHTMLData("/servers/server/stat/regions?serverId=" + serverId).catch(function () {
				return null
			})
		})
		return dashboardBuildFallbackCountryStats(regionPageDataList, function (count) {
			return teaweb.formatNumber(count) + "次"
		})
	}

	this.loadDashboardFallback = async function () {
		if (this.isLoadingFallbackStats) {
			return
		}
		if (this.topNodeStats.length > 0 && this.topCountryStats.length > 0) {
			return
		}

		this.isLoadingFallbackStats = true
		try {
			let dataPackage = this.loadDashboardFallbackCache()
			if (dataPackage == null) {
				let topNodeStats = []
				let topCountryStats = []

				if (this.topNodeStats.length == 0) {
					topNodeStats = await this.fetchTopNodeStatsFallback()
				}
				if (this.topCountryStats.length == 0) {
					topCountryStats = await this.fetchTopCountryStatsFallback()
				}

				dataPackage = {
					topNodeStats: topNodeStats,
					topCountryStats: topCountryStats
				}
				this.saveDashboardFallbackCache(dataPackage)
			}

			if (this.topNodeStats.length == 0 && Array.isArray(dataPackage.topNodeStats) && dataPackage.topNodeStats.length > 0) {
				this.topNodeStats = dataPackage.topNodeStats
				this.isTopNodeFallback = true
				this.$delay(function () {
					this.reloadTopNodesChart()
				})
			}

			if (this.topCountryStats.length == 0 && Array.isArray(dataPackage.topCountryStats) && dataPackage.topCountryStats.length > 0) {
				this.topCountryStats = dataPackage.topCountryStats
				this.topCountryStatsKey++
				this.isTopCountryFallback = true
			}
		} catch (e) {
			console.error("load dashboard fallback failed", e)
		} finally {
			this.isLoadingFallbackStats = false
		}
	}

	this.$delay(function () {
		// 整体图表
		this.$post("$")
			.success(function (resp) {
				for (let k in resp.data) {
					this[k] = resp.data[k]
				}

				this.todayCountIPsFormat = teaweb.formatNumber(this.todayCountIPs)

				this.isLoading = false

				this.$delay(function () {
					this.reloadHourlyTrafficChart()
					this.reloadHourlyRequestsChart()
					this.reloadTopDomainsChart()
					this.reloadTopNodesChart()

					if (this.topNodeStats.length == 0 || this.topCountryStats.length == 0) {
						this.loadDashboardFallback()
					}
				})

				// 节点数据
				this.$delay(function () {
					this.reloadNodeValues()
				}, 200)
			})
	})

	this.selectTrafficTab = function (tab) {
		this.trafficTab = tab
		if (tab == "hourly") {
			this.$delay(function () {
				this.reloadHourlyTrafficChart()
			})
		} else if (tab == "daily") {
			this.$delay(function () {
				this.reloadDailyTrafficChart()
			})
		}
	}

	this.reloadHourlyTrafficChart = function () {
		let stats = this.hourlyTrafficStats
		this.reloadTrafficChart("hourly-traffic-chart-box", stats, function (args) {
			let index = args.dataIndex
			let cachedRatio = 0
			let attackRatio = 0
			if (stats[index].bytes > 0) {
				cachedRatio = Math.round(stats[index].cachedBytes * 10000 / stats[index].bytes) / 100
				attackRatio = Math.round(stats[index].attackBytes * 10000 / stats[index].bytes) / 100
			}

			return stats[index].day + " " + stats[index].hour + "时<br/>总流量：" + teaweb.formatBytes(stats[index].bytes) + "<br/>缓存流量：" + teaweb.formatBytes(stats[index].cachedBytes) + "<br/>缓存命中率：" + cachedRatio + "%<br/>拦截攻击流量：" + teaweb.formatBytes(stats[index].attackBytes) + "<br/>拦截比例：" + attackRatio + "%"
		})
	}

	this.reloadDailyTrafficChart = function () {
		let stats = this.dailyTrafficStats
		this.reloadTrafficChart("daily-traffic-chart-box", stats, function (args) {
			let index = args.dataIndex
			let cachedRatio = 0
			let attackRatio = 0
			if (stats[index].bytes > 0) {
				cachedRatio = Math.round(stats[index].cachedBytes * 10000 / stats[index].bytes) / 100
				attackRatio = Math.round(stats[index].attackBytes * 10000 / stats[index].bytes) / 100
			}

			return stats[index].day + "<br/>总流量：" + teaweb.formatBytes(stats[index].bytes) + "<br/>缓存流量：" + teaweb.formatBytes(stats[index].cachedBytes) + "<br/>缓存命中率：" + cachedRatio + "%<br/>拦截攻击流量：" + teaweb.formatBytes(stats[index].attackBytes) + "<br/>拦截比例：" + attackRatio + "%"
		})
	}

	this.reloadTrafficChart = function (chartId, stats, tooltipFunc) {
		let axis = teaweb.bytesAxis(stats, function (v) {
			return v.bytes
		})
		let chartBox = document.getElementById(chartId)
		let chart = teaweb.initChart(chartBox)
		let option = {
			xAxis: {
				data: stats.map(function (v) {
					if (v.hour != null) {
						return v.hour
					}
					return v.day
				})
			},
			yAxis: {
				axisLabel: {
					formatter: function (v) {
						return v + axis.unit
					}
				}
			},
			tooltip: {
				show: true,
				trigger: "item",
				backgroundColor: getCssVariable('--color-bg', '#app'),
				borderColor: getCssVariable('--color-border', '#app'),
				textStyle: {
					color: getCssVariable('--color-text-active', '#app'),
				},
				formatter: tooltipFunc,
			},
			grid: {
				left: 50,
				top: 40,
				right: 20,
				bottom: 20
			},
			series: [
				{
					name: "总流量",
					type: "line",
					data: stats.map(function (v) {
						return v.bytes / axis.divider;
					}),
					itemStyle: {
						color: getCssVariable('--color-text-active', '#'+chartId),
					},
					lineStyle: {
						color: getCssVariable('--color-text-active', '#'+chartId),
					},
					areaStyle: {
						color: getCssVariable('--color-text-active', '#'+chartId),
					},
					smooth: true
				},
				{
					name: "缓存流量",
					type: "line",
					data: stats.map(function (v) {
						return v.cachedBytes / axis.divider;
					}),
					itemStyle: {
						color: "#61A0A8"
					},
					lineStyle: {
						color: "#61A0A8"
					},
					areaStyle: {},
					smooth: true
				},
				{
					name: "攻击流量",
					type: "line",
					data: stats.map(function (v) {
						return v.attackBytes / axis.divider;
					}),
					itemStyle: {
						color: "#F39494"
					},
					areaStyle: {
						color: "#F39494"
					},
					smooth: true
				}
			],
			legend: {
				data: ["总流量", "缓存流量", "攻击流量"],
				textStyle: {
					color: getCssVariable('--color-text'),
				},
			},
			animation: false
		}
		chart.setOption(option)
		chart.resize()
	}

	/**
	 * 请求数统计
	 */
	this.requestsTab = "hourly"

	this.selectRequestsTab = function (tab) {
		this.requestsTab = tab
		if (tab == "hourly") {
			this.$delay(function () {
				this.reloadHourlyRequestsChart()
			})
		} else if (tab == "daily") {
			this.$delay(function () {
				this.reloadDailyRequestsChart()
			})
		}
	}

	this.reloadHourlyRequestsChart = function () {
		let stats = this.hourlyTrafficStats
		this.reloadRequestsChart("hourly-requests-chart", "请求数统计", stats, function (args) {
			let index = args.dataIndex
			let cachedRatio = 0
			let attackRatio = 0
			if (stats[index].countRequests > 0) {
				cachedRatio = Math.round(stats[index].countCachedRequests * 10000 / stats[index].countRequests) / 100
				attackRatio = Math.round(stats[index].countAttackRequests * 10000 / stats[index].countRequests) / 100
			}

			return stats[index].day + " " + stats[index].hour + "时<br/>总请求数：" + teaweb.formatNumber(stats[index].countRequests) + "<br/>缓存请求数：" + teaweb.formatNumber(stats[index].countCachedRequests) + "<br/>缓存命中率：" + cachedRatio + "%<br/>拦截攻击数：" + teaweb.formatNumber(stats[index].countAttackRequests) + "<br/>拦截比例：" + attackRatio + "%"
		})
	}

	this.reloadDailyRequestsChart = function () {
		let stats = this.dailyTrafficStats
		this.reloadRequestsChart("daily-requests-chart", "请求数统计", stats, function (args) {
			let index = args.dataIndex
			let cachedRatio = 0
			let attackRatio = 0
			if (stats[index].countRequests > 0) {
				cachedRatio = Math.round(stats[index].countCachedRequests * 10000 / stats[index].countRequests) / 100
				attackRatio = Math.round(stats[index].countAttackRequests * 10000 / stats[index].countRequests) / 100
			}

			return stats[index].day + "<br/>总请求数：" + teaweb.formatNumber(stats[index].countRequests) + "<br/>缓存请求数：" + teaweb.formatNumber(stats[index].countCachedRequests) + "<br/>缓存命中率：" + cachedRatio + "%<br/>拦截攻击数：" + teaweb.formatNumber(stats[index].countAttackRequests) + "<br/>拦截比例：" + attackRatio + "%"
		})
	}

	this.reloadRequestsChart = function (chartId, name, stats, tooltipFunc) {
		let chartBox = document.getElementById(chartId)
		if (chartBox == null) {
			return
		}

		let axis = teaweb.countAxis(stats, function (v) {
			return Math.max(v.countRequests, v.countCachedRequests)
		})

		let chart = teaweb.initChart(chartBox)
		let option = {
			xAxis: {
				data: stats.map(function (v) {
					if (v.hour != null) {
						return v.hour
					}
					if (v.day != null) {
						return v.day
					}
					return ""
				})
			},
			yAxis: {
				axisLabel: {
					formatter: function (value) {
						return value + axis.unit
					}
				}
			},
			tooltip: {
				show: true,
				trigger: "item",
				backgroundColor: getCssVariable('--color-bg', '#app'),
				borderColor: getCssVariable('--color-border', '#app'),
				textStyle: {
					color: getCssVariable('--color-text-active', '#app'),
				},
				formatter: tooltipFunc,
			},
			grid: {
				left: 50,
				top: 40,
				right: 20,
				bottom: 20
			},
			series: [
				{
					name: "请求数",
					type: "line",
					data: stats.map(function (v) {
						return v.countRequests / axis.divider
					}),
					itemStyle: {
						color: getCssVariable('--color-text-active', '#'+chartId),
					},
					lineStyle: {
						color: getCssVariable('--color-text-active', '#'+chartId),
					},
					areaStyle: {
						color: getCssVariable('--color-text-active', '#'+chartId),
					},
					smooth: true
				},
				{
					name: "缓存请求数",
					type: "line",
					data: stats.map(function (v) {
						return v.countCachedRequests / axis.divider
					}),
					itemStyle: {
						color: "#61A0A8"
					},
					areaStyle: {
						color: "#61A0A8"
					},
					smooth: true
				},
				{
					name: "攻击请求数",
					type: "line",
					data: stats.map(function (v) {
						return v.countAttackRequests / axis.divider;
					}),
					itemStyle: {
						color: "#F39494"
					},
					areaStyle: {
						color: "#F39494"
					},
					smooth: true
				}
			],
			legend: {
				data: ["请求数", "缓存请求数", "攻击请求数"],
				textStyle: {
					color: getCssVariable('--color-text'),
				},
			},
			animation: true
		}
		chart.setOption(option)
		chart.resize()
	}

	// 节点排行
	this.reloadTopNodesChart = function () {
		let that = this
		let axis = teaweb.countAxis(this.topNodeStats, function (v) {
			return v.countRequests
		})
		teaweb.renderBarChart({
			id: "top-nodes-chart",
			name: "节点",
			values: this.topNodeStats,
			x: function (v) {
				return v.nodeName
			},
			tooltip: function (args, stats) {
				return stats[args.dataIndex].nodeName + "<br/>请求数：" + " " + teaweb.formatNumber(stats[args.dataIndex].countRequests) + "<br/>流量：" + teaweb.formatBytes(stats[args.dataIndex].bytes)
			},
			value: function (v) {
				return v.countRequests / axis.divider;
			},
			axis: axis,
			click: function (args, stats) {
				window.location = "/clusters/cluster/node?nodeId=" + stats[args.dataIndex].nodeId + "&clusterId=" + that.clusterId
			}
		})
	}

	// 域名排行
	this.reloadTopDomainsChart = function () {
		let axis = teaweb.countAxis(this.topDomainStats, function (v) {
			return v.countRequests
		})
		teaweb.renderBarChart({
			id: "top-domains-chart",
			name: "域名",
			values: this.topDomainStats,
			x: function (v) {
				return v.domain
			},
			tooltip: function (args, stats) {
				return stats[args.dataIndex].domain + "<br/>请求数：" + " " + teaweb.formatNumber(stats[args.dataIndex].countRequests) + "<br/>流量：" + teaweb.formatBytes(stats[args.dataIndex].bytes)
			},
			value: function (v) {
				return v.countRequests / axis.divider;
			},
			axis: axis,
			click: function (args, stats) {
				let index = args.dataIndex
				window.location = "/servers/server?serverId=" + stats[index].serverId
			}
		})
	}

	// 绘制节点总体信息
	this.reloadNodeValues = function () {
		let reloadInterval = 20000
		this.$post(".values")
			.success(function (resp) {
				this.nodeValuesStat = resp.data.stat
				this.renderBandwidthGauge()
				this.renderCPUGauge()
				this.renderMemoryGauge()
				this.renderLoadGauge()

				if (resp.data.stat.todayTrafficFormat.length > 0) {
					let pieces = teaweb.splitFormat(resp.data.stat.todayTrafficFormat)
					this.todayTraffic = pieces[0]
					this.todayTrafficUnit = pieces[1]
				}

				this.yesterdayPercentFormat = resp.data.stat.yesterdayPercentFormat
			})
			.done(function () {
				this.$delay(function () {
					this.reloadNodeValues()
				}, reloadInterval)
			})
	}

	// 绘制gauge
	let lastBandwidthBytes = 0
	this.renderBandwidthGauge = function () {
		let bandwidthFormat = this.nodeValuesStat.totalTrafficPerSecondFormat
		let matchResult = bandwidthFormat.match(/^([0-9.]+)([a-zA-Z]+)$/)
		let size = parseFloat(matchResult[1])
		let unit = matchResult[2]
		this.nodeValuesStat.totalTrafficPerSecondSizeFormat = matchResult[1]
		this.nodeValuesStat.totalTrafficPerSecondUnitFormat = unit

		let max = size
		if (size < 10) {
			max = 10
		} else if (size < 100) {
			max = 100
		} else if (size < 1000) {
			max = 1000
		} else if (size < 1200) {
			max = 1200
		}

		let color = ""
		if (lastBandwidthBytes == 0) {
			lastBandwidthBytes = this.nodeValuesStat.totalTrafficBytesPerSecond
		}
		if (lastBandwidthBytes > 0 && lastBandwidthBytes != this.nodeValuesStat.totalTrafficBytesPerSecond) {
			let delta = Math.abs(lastBandwidthBytes - this.nodeValuesStat.totalTrafficBytesPerSecond) * 100 / lastBandwidthBytes
			if (delta > 20) {
				color = "red"
			} else if (delta > 10) {
				color = "yellow"
			}
			lastBandwidthBytes = this.nodeValuesStat.totalTrafficBytesPerSecond
		}

		teaweb.renderGaugeChart({
			id: "total-bandwidth-chart-box",
			name: "",
			min: 0,
			max: max,
			value: size,
			startAngle: 240,
			endAngle: -60,
			color: color,
			unit: "",
			detail: ""
		})
	}

	this.renderCPUGauge = function () {
		let avgCPUUsage = Math.round(this.nodeValuesStat.avgCPUUsage * 100) / 100
		let color = ""
		if (avgCPUUsage > 50) {
			color = "red"
		} else if (avgCPUUsage > 20) {
			color = "yellow"
		} else if (avgCPUUsage < 10) {
			color = "green"
		}

		let maxCPUUsage = Math.round(this.nodeValuesStat.maxCPUUsage * 100) / 100
		let maxColor = ""
		if (maxCPUUsage > 50) {
			maxColor = "red"
		} else if (maxCPUUsage > 20) {
			maxColor = "yellow"
		} else if (maxCPUUsage < 10) {
			maxColor = "green"
		}

		teaweb.renderPercentChart({
			id: "all-cpu-chart-box",
			name: "平均CPU用量",
			unit: "%",
			total: 100,
			value: avgCPUUsage,
			color: color,
			max: maxCPUUsage,
			maxColor: maxColor,
			maxName: "最大CPU用量"
		})
	}

	this.renderMemoryGauge = function () {
		let avgMemoryUsage = Math.round(this.nodeValuesStat.avgMemoryUsage * 100) / 100
		let color = ""
		if (avgMemoryUsage > 80) {
			color = "red"
		} else if (avgMemoryUsage > 60) {
			color = "yellow"
		} else if (avgMemoryUsage < 20) {
			color = "green"
		}

		let maxMemoryUsage = Math.round(this.nodeValuesStat.maxMemoryUsage * 100) / 100
		let maxColor = ""
		if (maxMemoryUsage > 80) {
			maxColor = "red"
		} else if (maxMemoryUsage > 60) {
			maxColor = "yellow"
		} else if (maxMemoryUsage < 20) {
			maxColor = "green"
		}

		teaweb.renderPercentChart({
			id: "all-memory-chart-box",
			name: "平均内存用量",
			total: 100,
			unit: "%",
			value: avgMemoryUsage,
			color: color,
			max: maxMemoryUsage,
			maxColor: maxColor,
			maxName: "最大内存用量"
		})
	}

	this.renderLoadGauge = function () {
		let avgLoad1min = Math.round(this.nodeValuesStat.avgLoad1min * 100) / 100
		let color = ""
		if (avgLoad1min > 20) {
			color = "red"
		} else if (avgLoad1min > 5) {
			color = "yellow"
		} else {
			color = "green"
		}
		if (avgLoad1min > 10) {
			avgLoad1min = 10
		}

		let maxLoad1min = Math.round(this.nodeValuesStat.maxLoad1min * 100) / 100
		let maxColor = ""
		if (maxLoad1min > 20) {
			maxColor = "red"
		} else if (maxLoad1min > 5) {
			maxColor = "yellow"
		} else {
			maxColor = "green"
		}
		if (maxLoad1min > 20) {
			maxLoad1min = 20
		}

		teaweb.renderPercentChart({
			id: "all-load-chart-box",
			name: "平均负载",
			unit: "",
			value: avgLoad1min,
			total: 20,
			color: color,
			max: maxLoad1min,
			maxColor: maxColor,
			maxName: "最大负载"
		})
	}

	/**
	 * 升级提醒
	 */
	this.closeMessage = function (e) {
		let target = e.target
		while (true) {
			target = target.parentNode
			if (target.tagName.toUpperCase() == "DIV") {
				target.style.cssText = "display: none"
				break
			}
		}
	}

	// 重启本地API节点
	this.isRestartingLocalAPINode = false
	this.restartAPINode = function () {
		if (this.isRestartingLocalAPINode) {
			return
		}
		if (this.localLowerVersionAPINode == null) {
			return
		}
		this.isRestartingLocalAPINode = true
		this.localLowerVersionAPINode.isRestarting = true
		this.$post("/dashboard/restartLocalAPINode")
			.params({
				"exePath": this.localLowerVersionAPINode.exePath
			})
			.timeout(300)
			.success(function () {
				teaweb.reload()
			})
			.done(function () {
				this.isRestartingLocalAPINode = false
				this.localLowerVersionAPINode.isRestarting = false
			})
	}

	// 关闭XFF提示
	this.dismissXFFPrompt = function () {
		this.$post("/settings/security/dismissXFFPrompt")
			.success(function () {
				teaweb.reload()
			})
	}
})
}

if (typeof (module) != "undefined" && module.exports != null) {
	module.exports = {
		dashboardParseTeaActionDataFromHTML: dashboardParseTeaActionDataFromHTML,
		dashboardExtractMaxPage: dashboardExtractMaxPage,
		dashboardMergeTopNodeStats: dashboardMergeTopNodeStats,
		dashboardBuildFallbackCountryStats: dashboardBuildFallbackCountryStats
	}
}
