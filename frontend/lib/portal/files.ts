/** Uploaded demo files remain in this browser, never sent to a service. */
async function store() { return new Promise<IDBDatabase>((resolve, reject) => { const req = indexedDB.open("aicte-demo-files", 1); req.onupgradeneeded = () => req.result.createObjectStore("files"); req.onsuccess = () => resolve(req.result); req.onerror = () => reject(new Error("Browser file storage is unavailable.")); }); }
export async function putFile(id: string, file: File) { const db = await store(); try {
    await new Promise<void>((resolve, reject) => { const tx = db.transaction("files", "readwrite"); tx.objectStore("files").put(file, id); tx.oncomplete = () => resolve(); tx.onerror = () => reject(new Error("File storage failed. Try a smaller file.")); });
}
finally {
    db.close();
} }
export async function getFile(id: string): Promise<Blob | undefined> { const db = await store(); try {
    return await new Promise((resolve, reject) => { const req = db.transaction("files").objectStore("files").get(id); req.onsuccess = () => resolve(req.result); req.onerror = () => reject(new Error("File could not be loaded.")); });
}
finally {
    db.close();
} }
export function download(blob: Blob, name: string) { const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = name; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
