// 游戏加载器 - 从 IndexedDB 加载游戏文件
// 这个文件是固定的，不需要每次导出时生成

// IndexedDB 配置（与 loading.html 保持一致）
const DB_NAME = 'hres_game_files';
const DB_VERSION = 1;
const STORE_NAME = 'files';

let db = null;

// 初始化 IndexedDB
async function initDB() {
	return new Promise((resolve, reject) => {
		const request = indexedDB.open(DB_NAME, DB_VERSION);

		request.onerror = () => reject(request.error);
		request.onsuccess = () => {
			db = request.result;
			resolve(db);
		};

		request.onupgradeneeded = (event) => {
			const db = event.target.result;
			if (!db.objectStoreNames.contains(STORE_NAME)) {
				db.createObjectStore(STORE_NAME);
			}
		};
	});
}

// 从 IndexedDB 读取文件
async function getFileFromDB(filename) {
	return new Promise((resolve, reject) => {
		const transaction = db.transaction([STORE_NAME], 'readonly');
		const store = transaction.objectStore(STORE_NAME);
		const request = store.get(filename);

		request.onerror = () => reject(request.error);
		request.onsuccess = () => {
			resolve(request.result);
		};
	});
}

// 主加载函数 - 从 IndexedDB 加载游戏文件
async function loadGameFromIndexedDB(engine, statusTextElement, statusProgressElement, setStatusText, updateProgress, setStatusMode, displayFailureNotice, fileSizes) {
	const pckSize = fileSizes['index.pck'];
	const wasmSize = fileSizes['index.wasm'];
	const totalSize = pckSize + wasmSize;
	
	console.log('从 IndexedDB 加载游戏文件...');
	
	// 初始化 IndexedDB
	await initDB();
	
	// 从 IndexedDB 读取 PCK 文件
	setStatusText('正在从本地缓存加载游戏资源包...');
	let pckArrayBuffer = null;
	let actualPckSize = 0;
	let actualWasmSize = 0;
	let actualTotalSize = 0;
	
	try {
		const cachedPck = await getFileFromDB('index.pck');
		if (!cachedPck) {
			throw new Error('PCK 文件未找到。请先访问加载页面下载文件。');
		}
		console.log('从 IndexedDB 读取 PCK 文件成功，大小:', cachedPck.byteLength);
		pckArrayBuffer = cachedPck;
		actualPckSize = cachedPck.byteLength;
		updateProgress(actualPckSize, actualPckSize + wasmSize, '游戏资源包加载完成...');
	} catch (error) {
		console.error('从 IndexedDB 读取 PCK 失败:', error);
		throw new Error('无法从本地缓存加载游戏资源包。请先访问加载页面下载文件。');
	}
	
	console.log('PCK 文件准备完成，预加载到引擎...');
	setStatusText('正在预加载游戏资源...');
	updateProgress(actualPckSize, actualPckSize + wasmSize, '正在预加载游戏资源...');
	
	// 使用 preloadFile 的 ArrayBuffer 版本预加载 PCK 文件（使用实际文件大小）
	await engine.preloadFile(pckArrayBuffer, 'index.pck', actualPckSize);
	
	console.log('PCK 文件预加载完成，加载 WASM 引擎...');
	
	// 从 IndexedDB 验证 WASM 文件是否存在（不检查大小，因为每次导出大小可能不同）
	setStatusText('正在验证游戏引擎文件...');
	try {
		const cachedWasm = await getFileFromDB('index.wasm');
		if (!cachedWasm) {
			throw new Error('WASM 文件未找到。请先访问加载页面下载文件。');
		}
		console.log('WASM 文件在 IndexedDB 中验证成功，大小:', cachedWasm.byteLength);
		actualWasmSize = cachedWasm.byteLength;
		actualTotalSize = actualPckSize + actualWasmSize;
		updateProgress(actualTotalSize, actualTotalSize, '游戏引擎准备完成...');
	} catch (error) {
		console.error('从 IndexedDB 验证 WASM 失败:', error);
		throw new Error('无法从本地缓存验证游戏引擎。请先访问加载页面下载文件。');
	}
	
	// 尝试注册 Service Worker 来拦截 WASM 请求
	setStatusText('正在设置 WASM 加载...');
	let useServiceWorker = false;
	
	if ('serviceWorker' in navigator) {
		if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
			console.warn('Service Worker 需要 HTTPS 或 localhost，当前协议:', location.protocol);
			useServiceWorker = false;
		} else {
			try {
				const existingRegistration = await navigator.serviceWorker.getRegistration();
				
				if (!existingRegistration) {
					try {
						const registration = await navigator.serviceWorker.register('wasm-service-worker.js', {
							scope: './'
						});
						console.log('WASM Service Worker 注册成功，scope:', registration.scope);
						
						await Promise.race([
							navigator.serviceWorker.ready,
							new Promise((_, reject) => setTimeout(() => reject(new Error('Service Worker 激活超时')), 3000))
						]);
						
						if (navigator.serviceWorker.controller) {
							useServiceWorker = true;
							console.log('WASM Service Worker 已就绪并控制页面');
						} else {
							console.warn('WASM Service Worker 已注册但未控制页面，可能需要刷新');
							useServiceWorker = false;
						}
					} catch (swError) {
						console.warn('注册 WASM Service Worker 失败，将使用浏览器缓存:', swError);
						useServiceWorker = false;
					}
				} else {
					console.log('检测到已有 Service Worker（可能是 coi.js），将使用浏览器缓存加载 WASM');
					try {
						const newRegistration = await navigator.serviceWorker.register('wasm-service-worker.js', {
							scope: './'
						});
						console.log('尝试注册新的 WASM Service Worker');
						await Promise.race([
							navigator.serviceWorker.ready,
							new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 2000))
						]);
						if (navigator.serviceWorker.controller) {
							useServiceWorker = true;
						} else {
							useServiceWorker = false;
						}
					} catch (error) {
						console.log('无法注册新的 Service Worker（已有其他 SW），将使用浏览器缓存:', error.message);
						useServiceWorker = false;
					}
				}
			} catch (error) {
				console.warn('Service Worker 检查失败，将使用浏览器缓存:', error);
				useServiceWorker = false;
			}
		}
	} else {
		console.warn('浏览器不支持 Service Worker');
		useServiceWorker = false;
	}
	
	// 加载 WASM 文件
	setStatusText('正在加载游戏引擎...');
	updateProgress(actualPckSize, actualTotalSize, '正在从本地缓存加载游戏引擎...');
	
	const R2_BASE_URL = 'https://cdn.hres.world';
	
	// 使用 GODOT_CONFIG 中的 wasmSize 来调用 engine.load()，因为 Godot 需要预期大小
	// 但进度显示使用实际文件大小
	if (useServiceWorker) {
		const wasmBasePath = './index';
		try {
			await engine.load(wasmBasePath, wasmSize);
			console.log('使用 Service Worker 从 IndexedDB 加载 WASM 成功');
		} catch (error) {
			console.warn('Service Worker 加载失败，fallback 到浏览器缓存:', error);
			const wasmBasePath = `${R2_BASE_URL}/index`;
			await engine.load(wasmBasePath, wasmSize);
			console.log('使用浏览器缓存加载 WASM 成功');
		}
	} else {
		const wasmBasePath = `${R2_BASE_URL}/index`;
		await engine.load(wasmBasePath, wasmSize);
		console.log('使用浏览器缓存加载 WASM 成功（从 IndexedDB 下载后浏览器已缓存）');
	}
	
	console.log('WASM 文件加载完成，准备初始化...');
	setStatusText('正在初始化游戏引擎...');
	updateProgress(actualTotalSize, actualTotalSize, '正在初始化游戏引擎...');
	
	// 初始化引擎
	await engine.init();
	
	console.log('引擎初始化完成，启动游戏...');
	setStatusText('正在启动游戏...');
	
	// 设置启动参数
	engine.config.args = ['--main-pack', 'index.pck'].concat(engine.config.args);
	
	// 启动游戏
	await engine.start({
		'onProgress': function (current, total) {
			if (current > 0 && total > 0) {
				const percent = Math.round((current / total) * 100);
				updateProgress(current, total, `正在启动游戏 (${percent}%)...`);
			} else {
				setStatusText('正在启动游戏...');
			}
		},
	});
	
	setStatusMode('hidden');
}
