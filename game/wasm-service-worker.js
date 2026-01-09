// Service Worker 用于从 IndexedDB 返回 WASM 文件
const DB_NAME = 'hres_game_files';
const DB_VERSION = 1;
const STORE_NAME = 'files';

self.addEventListener('install', (event) => {
	self.skipWaiting();
});

self.addEventListener('activate', (event) => {
	event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
	const url = new URL(event.request.url);
	// 拦截同源的 WASM 文件请求（如 ./index.wasm）
	if (url.pathname.endsWith('.wasm') && url.origin === self.location.origin) {
		event.respondWith(handleWasmRequest(event.request));
	}
});

async function handleWasmRequest(request) {
	try {
		// 打开 IndexedDB
		const db = await openDB();
		
		// 从 IndexedDB 读取 WASM 文件
		const wasmData = await getFileFromDB(db, 'index.wasm');
		
		if (!wasmData) {
			// 如果 IndexedDB 中没有，尝试回退到原始请求（虽然不应该发生）
			console.error('Service Worker: IndexedDB 中没有找到 WASM 文件');
			return new Response('WASM file not found in IndexedDB', { status: 404 });
		}
		
		// 返回 WASM 数据作为 Response
		return new Response(wasmData, {
			headers: {
				'Content-Type': 'application/wasm',
				'Content-Length': wasmData.byteLength.toString(),
			},
		});
	} catch (error) {
		console.error('Service Worker: 从 IndexedDB 读取 WASM 失败:', error);
		return new Response('Failed to load WASM from IndexedDB', { status: 500 });
	}
}

function openDB() {
	return new Promise((resolve, reject) => {
		const request = indexedDB.open(DB_NAME, DB_VERSION);
		
		request.onerror = () => reject(request.error);
		request.onsuccess = () => resolve(request.result);
		
		request.onupgradeneeded = (event) => {
			const db = event.target.result;
			if (!db.objectStoreNames.contains(STORE_NAME)) {
				db.createObjectStore(STORE_NAME);
			}
		};
	});
}

function getFileFromDB(db, filename) {
	return new Promise((resolve, reject) => {
		const transaction = db.transaction([STORE_NAME], 'readonly');
		const store = transaction.objectStore(STORE_NAME);
		const request = store.get(filename);
		
		request.onerror = () => reject(request.error);
		request.onsuccess = () => resolve(request.result);
	});
}
