document.addEventListener('DOMContentLoaded', function() {
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('upload_files');
// uploadArea.addEventListener('click', () => fileInput.click());

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
	uploadArea.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
	e.preventDefault();
	e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
	uploadArea.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
	uploadArea.addEventListener(eventName, unhighlight, false);
});

function highlight() {
	uploadArea.classList.add('dragging');
}

function unhighlight() {
	uploadArea.classList.remove('dragging');
}

uploadArea.addEventListener('drop', handleDrop, false);

async function handleDrop(e) {
	e.preventDefault();
	let uploadFailed = "";
	let files = await dropFiles(e);
	if (files) {
		files.forEach(async (f) => {
			let ret = await uploadFile(f.file, f.path);
			if ( ret !== true) {
				uploadFailed += ret;
			}
		});
	}
	if (uploadFailed != "") {
		window.alert(uploadFailed);
	}

	//clean cache
	await purgeCache().then(() => {
		window.location.reload();
	});
}

async function dropFiles(event) {
	if (
	  event.dataTransfer.types[0] !== "Files" ||
	  !event.dataTransfer.items
	) {
	  return;
	}

	const entries = [...event.dataTransfer.items].map((item) =>
	  item.webkitGetAsEntry()
	);

	const allEntries = await traverseFileTree(entries);

	let files = await Promise.all(
	  allEntries.map(
		(e) =>
			new Promise((resolve, reject) => e.entry.file((file) => resolve({ file, path: e.path }), reject))
	  )
	);

	return files;
  }

  async function traverseFileTree(entries) {
	let files = [];

	async function traverse(entries, path = '') {
	  for (let i = 0; i < entries.length; i++) {
		const entry = entries[i];

		if (entry.isFile) {
		  files.push({entry: entry, path: path});
		} else if (entry.isDirectory) {
		  const childEntries = await new Promise((resolve, reject) =>
			entry.createReader().readEntries(resolve, reject)
		  );
		  await traverse(childEntries, path + entry.name + '/');
		}
	  }
	}

	return traverse(entries).then(() => files);
  }

fileInput.addEventListener('change', async function() {
	for (let file of this.files) {
		await uploadFile(file);
	}
});

async function processEntry(entry, path = '') {
	if (entry.isFile) {
		const file = await new Promise((resolve) => entry.file(resolve));
		await uploadFile(file, path );
	} else if (entry.isDirectory) {
		const reader = entry.createReader();
		const entries = await new Promise((resolve) => reader.readEntries(resolve));
		for (let childEntry of entries) {
			await processEntry(childEntry, path + entry.name + '/');
		}
	}
}

async function purgeCache() {
	const noticeEl = document.getElementById('upload-notice');
	const formUpload = document.getElementById('upload-form');
	const formData = new FormData(formUpload);
	fetch('/servers/server/settings/page/purge', { method: 'POST', body: formData }).then(response => response.json())
	.then(data => {
	  noticeEl.setHTMLUnsafe('正在清理缓存');
	})
	.catch((error) => {
	  console.error('Error:', error);
	});
}

async function uploadFile(file, customPath = '') {
	const filePath = file.webkitRelativePath || customPath;
	// console.log('File to upload:', file.name, 'Path:', filePath);
	const noticeEl = document.getElementById('upload-notice');
	const formUpload = document.getElementById('upload-form');
	const formData = new FormData(formUpload);
	formData.append('path', filePath);
	formData.append('file', file);
	try {
		const response = await fetch('/servers/server/settings/page/fileUpload', { method: 'POST',
		 body: formData });
		 const data = await response.json();
		 if (data.code != 200) {
			return `${file.name}: ${data.message}`;
		}else{
			return true;
		}
	} catch (error) {
		return `${file.name}: ${error.message}`;
	}
	// .then(data => {
	// 	if (data.code != 200) {
	// 		uploadFailed = (file.name + data.message);
	// 	}else{
	//   	noticeEl.setHTMLUnsafe(file.name + ' uploaded successfully');
	// 	}
	// })
	// .catch((error) => {
	//   console.error(error);
	// });
}

});

Tea.context(function () {
	this.success = NotifyReloadSuccess("保存成功")
	this.serverPagesSetting = function () {
		teaweb.popup("/servers/server/settings/page/setting?serverId=" + this.serverId, {
			title: '调整存储限制',
			height: "26em",
			callback: function () {
				teaweb.success("保存成功", function () {
					teaweb.reload()
				})
			}
		})
	}
	this.deleteFile = function (filePath) {
		teaweb.confirm("确定要删除吗？", function () {
			const formUpload = document.getElementById('upload-form');
			const formData = new FormData(formUpload);
			formData.append('path', filePath);
			this.$post(".fileDelete")
				.params(formData)
				.success(function () {
					const formUpload = document.getElementById('upload-form');
					const formData = new FormData(formUpload);
					fetch('/servers/server/settings/page/purge', { method: 'POST', body: formData }).then(response => response.json())
					.then(data => {
						teaweb.reload();
					})
					.catch((error) => {
					  console.error('Error:', error);
					});
					
				})
		})
	}

})