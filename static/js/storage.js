/**
 * Browser storage for emagrecimento dashboard.
 * Persists report data, form fields, and file blobs in IndexedDB
 * so the user does not need to re-upload on each visit.
 */
(function () {
    const DB_NAME = 'emagrecimento-db';
    const STORE_NAME = 'session';
    const DB_VERSION = 1;

    function openDB() {
        return new Promise((resolve, reject) => {
            const req = indexedDB.open(DB_NAME, DB_VERSION);
            req.onerror = () => reject(req.error);
            req.onsuccess = () => resolve(req.result);
            req.onupgradeneeded = (e) => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME, { keyPath: 'id' });
                }
            };
        });
    }

    const SESSION_ID = 'last';

    window.emagrecimentoStorage = {
        /**
         * Save session: report, form fields, and file blobs.
         * @param {Object} data - { report, formFields, zipFile, zipFilename, pdfFile, pdfFilename, withingsZipFile, withingsZipFilename }
         */
        async save(data) {
            const db = await openDB();
            return new Promise((resolve, reject) => {
                const tx = db.transaction(STORE_NAME, 'readwrite');
                const store = tx.objectStore(STORE_NAME);
                const entry = {
                    id: SESSION_ID,
                    report: data.report || null,
                    formFields: data.formFields || {},
                    zipFilename: data.zipFilename || null,
                    pdfFilename: data.pdfFilename || null,
                    withingsZipFilename: data.withingsZipFilename || null,
                    agentDiary: data.agentDiary || null,
                    savedAt: new Date().toISOString(),
                };
                if (data.zipFile instanceof Blob) {
                    entry.zipBlob = data.zipFile;
                }
                if (data.pdfFile instanceof Blob) {
                    entry.pdfBlob = data.pdfFile;
                }
                if (data.withingsZipFile instanceof Blob) {
                    entry.withingsZipBlob = data.withingsZipFile;
                }
                const req = store.put(entry);
                req.onsuccess = () => resolve();
                req.onerror = () => reject(req.error);
                tx.oncomplete = () => db.close();
            });
        },

        /**
         * Load saved session.
         * @returns {Promise<{report, formFields, zipFile, zipFilename, pdfFile, pdfFilename}|null>}
         */
        async load() {
            const db = await openDB();
            return new Promise((resolve, reject) => {
                const tx = db.transaction(STORE_NAME, 'readonly');
                const store = tx.objectStore(STORE_NAME);
                const req = store.get(SESSION_ID);
                req.onsuccess = () => {
                    const row = req.result;
                    if (!row) {
                        db.close();
                        resolve(null);
                        return;
                    }
                    let zipFile = null;
                    let pdfFile = null;
                    let withingsZipFile = null;
                    if (row.zipBlob && row.zipFilename) {
                        zipFile = new File([row.zipBlob], row.zipFilename, { type: 'application/zip' });
                    }
                    if (row.pdfBlob && row.pdfFilename) {
                        pdfFile = new File([row.pdfBlob], row.pdfFilename, { type: 'application/pdf' });
                    }
                    if (row.withingsZipBlob && row.withingsZipFilename) {
                        withingsZipFile = new File([row.withingsZipBlob], row.withingsZipFilename, { type: 'application/zip' });
                    }
                    db.close();
                    resolve({
                        report: row.report || null,
                        formFields: row.formFields || {},
                        zipFile,
                        zipFilename: row.zipFilename || null,
                        pdfFile,
                        pdfFilename: row.pdfFilename || null,
                        withingsZipFile,
                        withingsZipFilename: row.withingsZipFilename || null,
                        agentDiary: row.agentDiary || null,
                        savedAt: row.savedAt,
                    });
                };
                req.onerror = () => reject(req.error);
            });
        },

        /**
         * Clear saved session.
         */
        async clear() {
            const db = await openDB();
            return new Promise((resolve, reject) => {
                const tx = db.transaction(STORE_NAME, 'readwrite');
                const store = tx.objectStore(STORE_NAME);
                const req = store.delete(SESSION_ID);
                req.onsuccess = () => resolve();
                req.onerror = () => reject(req.error);
                tx.oncomplete = () => db.close();
            });
        },
    };
})();
