let currentKBs = [];
let activeKBId = null;
let allowedFileTypes = ['pdf', 'txt'];
let pollingInterval = null;

document.addEventListener('DOMContentLoaded', async () => {
    await fetchConfig();
    fetchKBs();
});

async function fetchConfig() {
    try {
        const data = await apiFetch('/kb/config');
        if (data.allowed_file_types) {
            allowedFileTypes = data.allowed_file_types;
            updateUploadUI();
        }
    } catch (e) {
        console.error("Failed to load config, using defaults.");
        updateUploadUI();
    }
}

function updateUploadUI() {
    const typesStr = allowedFileTypes.map(t => t.toUpperCase()).join('、');
    const hint = document.getElementById('uploadHint');
    if (hint) {
        hint.textContent = `已支持 ${typesStr}格式文件`;
    }

    const input = document.getElementById('uploadInput');
    if (input) {
        input.accept = allowedFileTypes.map(t => `.${t}`).join(',');
    }
}

// --- KB Management ---
async function fetchKBs() {
    showLoading('loading', true);
    document.getElementById('kbGrid').classList.add('hidden');
    document.getElementById('emptyState').classList.add('hidden');

    try {
        const data = await apiFetch(`/kb/list?tenant_id=${TENANT_ID}`);
        currentKBs = data;
        renderKBs(data);
    } catch (error) {
        showToast('加载失败: ' + error.message, 'error');
    } finally {
        showLoading('loading', false);
    }
}

function renderKBs(kbs) {
    const grid = document.getElementById('kbGrid');
    const empty = document.getElementById('emptyState');
    
    grid.innerHTML = '';
    
    if (kbs.length === 0) {
        grid.classList.add('hidden');
        empty.classList.remove('hidden');
        return;
    }
    
    empty.classList.add('hidden');
    grid.classList.remove('hidden');

    kbs.forEach(kb => {
        const card = document.createElement('div');
        card.className = 'bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow relative group cursor-pointer';
        card.onclick = (e) => {
            if (e.target.closest('button')) return;
            openKBDetails(kb.id);
        };
        
        card.innerHTML = `
            <div class="flex justify-between items-start mb-4">
                <div class="bg-blue-100 text-blue-600 w-10 h-10 rounded-lg flex items-center justify-center">
                    <i class="fa-solid fa-book"></i>
                </div>
                <div class="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onclick="openEditModal('${kb.id}')" class="text-gray-400 hover:text-blue-500 p-1.5 rounded-md hover:bg-blue-50 transition-colors" title="编辑">
                        <i class="fa-solid fa-pen"></i>
                    </button>
                    <button onclick="deleteKB('${kb.id}')" class="text-gray-400 hover:text-red-500 p-1.5 rounded-md hover:bg-red-50 transition-colors" title="删除">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>
            </div>
            <h3 class="text-lg font-bold text-gray-900 mb-2 truncate">${escapeHtml(kb.name)}</h3>
            <p class="text-gray-500 text-sm mb-4 line-clamp-2 h-10">${escapeHtml(kb.description || '暂无描述')}</p>
            <div class="flex items-center justify-between text-xs text-gray-400 pt-4 border-t border-gray-50">
                <span><i class="fa-regular fa-clock mr-1"></i>${formatDate(kb.created_at)}</span>
                <span class="bg-gray-100 px-2 py-1 rounded text-gray-500">ID: ${kb.id.slice(0,8)}...</span>
            </div>
        `;
        grid.appendChild(card);
    });
}

async function handleSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const btn = form.querySelector('button[type="submit"]');
    const spinner = document.getElementById('submitBtnSpinner');
    const btnText = document.getElementById('submitBtnText');
    const kbId = document.getElementById('kbId').value;
    const isEdit = !!kbId;

    btn.disabled = true;
    spinner.classList.remove('hidden');
    btnText.textContent = isEdit ? '保存中...' : '创建中...';

    const payload = {
        name: form.name.value,
        description: form.description.value,
        tenant_id: TENANT_ID
    };

    try {
        let url = '/kb/create';
        let method = 'POST';

        if (isEdit) {
            url = `/kb/${kbId}?tenant_id=${TENANT_ID}`;
            method = 'PUT';
        }

        await apiFetch(url, {
            method: method,
            body: payload
        });
        
        showToast(isEdit ? '知识库已更新' : '知识库创建成功');
        closeModal();
        fetchKBs();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btn.disabled = false;
        spinner.classList.add('hidden');
        btnText.textContent = isEdit ? '保存' : '创建';
    }
}

async function deleteKB(id) {
    if (!confirm('确定要删除这个知识库吗？此操作无法撤销。')) return;

    try {
        await apiFetch(`/kb/${id}?tenant_id=${TENANT_ID}`, {
            method: 'DELETE'
        });
        
        showToast('知识库已删除');
        fetchKBs();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// --- View Switching ---
function showDashboard() {
    document.getElementById('kbGrid').classList.remove('hidden');
    document.getElementById('kbDetails').classList.add('hidden');
    stopPolling();
    activeKBId = null;
    fetchKBs(); 
}

function openKBDetails(id) {
    const kb = currentKBs.find(k => k.id === id);
    if (!kb) return;
    
    activeKBId = id;
    document.getElementById('kbGrid').classList.add('hidden');
    document.getElementById('emptyState').classList.add('hidden');
    document.getElementById('kbDetails').classList.remove('hidden');
    
    document.getElementById('detailTitle').textContent = kb.name;
    document.getElementById('detailDesc').textContent = kb.description || '暂无描述';
    
    fetchDocuments(id);
}

// --- Document Management ---
async function fetchDocuments(kbId) {
    const tbody = document.getElementById('docListBody');
    const empty = document.getElementById('docEmptyState');
    
    tbody.innerHTML = '<tr><td colspan="5" class="px-6 py-4 text-center text-gray-500">加载中...</td></tr>';
    
    try {
        const docs = await apiFetch(`/kb/${kbId}/documents`);
        
        document.getElementById('docCount').textContent = docs.length;
        tbody.innerHTML = '';

        if (docs.length === 0) {
            empty.classList.remove('hidden');
            return;
        }
        
        empty.classList.add('hidden');
        
        const hasPendingOrRunning = docs.some(d => d.status === 'pending' || d.status === 'running');
        if (hasPendingOrRunning) {
            startPolling(kbId);
        } else {
            stopPolling();
        }

        docs.forEach(doc => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 flex items-center gap-2">
                    <i class="fa-regular fa-file-lines text-gray-400"></i>
                    ${escapeHtml(doc.filename)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${formatSize(doc.file_size)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${formatDate(doc.created_at)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    ${getStatusBadge(doc.status)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button onclick="downloadFile('${doc.id}', '${kbId}')" class="text-blue-600 hover:text-blue-900 mr-3">
                        <i class="fa-solid fa-download"></i>
                    </button>
                    <button onclick="deleteDocument('${doc.id}', '${kbId}')" class="text-red-600 hover:text-red-900">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="5" class="px-6 py-4 text-center text-red-500">加载失败: ${error.message}</td></tr>`;
    }
}

async function deleteDocument(docId, kbId) {
    if (!confirm('确定要删除这个文档吗？')) return;
    try {
        await apiFetch(`/kb/${kbId}/documents/${docId}`, { method: 'DELETE' });
        showToast('文档已删除');
        fetchDocuments(kbId);
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// --- Upload ---
async function handleFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) {
        await uploadFiles(files);
    }
    event.target.value = '';
}

function handleDragOver(event) {
    event.preventDefault();
    document.getElementById('dropzone').classList.add('border-blue-500', 'bg-blue-50');
}

function handleDragLeave(event) {
    event.preventDefault();
    document.getElementById('dropzone').classList.remove('border-blue-500', 'bg-blue-50');
}

function handleDrop(event) {
    event.preventDefault();
    document.getElementById('dropzone').classList.remove('border-blue-500', 'bg-blue-50');
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        uploadFiles(files);
    }
}

async function uploadFiles(files) {
    if (!activeKBId) return;

    // Validate types
    const validFiles = Array.from(files).filter(file => {
        const ext = file.name.split('.').pop().toLowerCase();
        return allowedFileTypes.includes(ext);
    });

    if (validFiles.length === 0) {
        showToast(`不支持的文件类型。仅支持: ${allowedFileTypes.join(', ')}`, 'error');
        return;
    }

    if (validFiles.length < files.length) {
        showToast(`部分文件被跳过（格式不支持）`, 'error');
    }

    showToast('正在上传...', 'info');

    let successCount = 0;
    let failCount = 0;

    for (const file of validFiles) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            await apiFetch(`/kb/${activeKBId}/documents/upload`, {
                method: 'POST',
                body: formData
            });
            successCount++;
        } catch (error) {
            console.error(`Upload failed for ${file.name}:`, error);
            failCount++;
        }
    }

    if (failCount === 0) {
        showToast(`成功上传 ${successCount} 个文件`);
    } else {
        showToast(`上传完成: ${successCount} 成功, ${failCount} 失败`, 'warning');
    }
    
    fetchDocuments(activeKBId);
}

// --- Helpers ---
function startPolling(kbId) {
    if (pollingInterval) return;
    pollingInterval = setInterval(() => {
        fetchDocuments(kbId);
    }, 3000);
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getStatusBadge(status) {
    const styles = {
        'pending': 'bg-gray-100 text-gray-800',
        'running': 'bg-blue-100 text-blue-800',
        'completed': 'bg-green-100 text-green-800',
        'failed': 'bg-red-100 text-red-800'
    };
    const labels = {
        'pending': '等待中',
        'running': '处理中',
        'completed': '已完成',
        'failed': '失败'
    };
    
    return `<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${styles[status] || styles['pending']}">
        ${labels[status] || status}
    </span>`;
}

function downloadFile(docId, kbId) {
    if (!docId || !kbId) {
        showToast('下载失败: 缺少参数', 'error');
        return;
    }
    
    // Create a hidden link to trigger the download
    const link = document.createElement('a');
    link.href = `${API_BASE}/kb/${kbId}/documents/${docId}/download`;
    link.download = ''; // Browser will use Content-Disposition filename
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// --- Modals ---
function openCreateModal() {
    document.getElementById('modal').classList.remove('hidden');
    document.getElementById('modalTitle').textContent = '新建知识库';
    document.getElementById('submitBtnText').textContent = '创建';
    document.getElementById('kbForm').reset();
    document.getElementById('kbId').value = '';
}

function openEditModal(id) {
    const kb = currentKBs.find(k => k.id === id);
    if (!kb) return;

    document.getElementById('modal').classList.remove('hidden');
    document.getElementById('modalTitle').textContent = '编辑知识库';
    document.getElementById('submitBtnText').textContent = '保存';
    
    document.getElementById('kbId').value = kb.id;
    document.getElementById('nameInput').value = kb.name;
    document.getElementById('descInput').value = kb.description || '';
}

function closeModal() {
    document.getElementById('modal').classList.add('hidden');
}
