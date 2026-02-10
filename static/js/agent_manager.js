let currentAgents = [];
let availableKBs = [];

document.addEventListener('DOMContentLoaded', async () => {
    await fetchKBs(); 
    fetchAgents();
});

// --- Data Loading ---
async function fetchKBs() {
    try {
        const data = await apiFetch(`/kb/list?tenant_id=${TENANT_ID}`);
        availableKBs = data;
    } catch (e) {
        console.error("Failed to load KBs:", e);
    }
}

async function fetchAgents() {
    showLoading('loading', true);
    document.getElementById('agentGrid').classList.add('hidden');
    document.getElementById('emptyState').classList.add('hidden');

    try {
        const data = await apiFetch(`/agent/agents?tenant_id=${TENANT_ID}`);
        currentAgents = data;
        renderAgents(data);
    } catch (error) {
        showToast('加载失败: ' + error.message, 'error');
    } finally {
        showLoading('loading', false);
    }
}

// --- Rendering ---
function renderAgents(agents) {
    const grid = document.getElementById('agentGrid');
    const empty = document.getElementById('emptyState');
    
    grid.innerHTML = '';
    
    if (agents.length === 0) {
        grid.classList.add('hidden');
        empty.classList.remove('hidden');
        return;
    }
    
    empty.classList.add('hidden');
    grid.classList.remove('hidden');

    agents.forEach(item => {
        const card = document.createElement('div');
        card.className = 'bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow relative group';
        
        // KB badges
        const kbBadges = item.knowledge_bases.map(kb => 
            `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 mr-1">
                <i class="fa-solid fa-book mr-1 text-[10px]"></i>${escapeHtml(kb.name)}
            </span>`
        ).join('');

        card.innerHTML = `
            <div class="flex justify-between items-start mb-4">
                <div class="bg-purple-100 text-purple-600 w-10 h-10 rounded-lg flex items-center justify-center">
                    <i class="fa-solid fa-robot"></i>
                </div>
                <div class="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onclick="openEditModal('${item.id}')" class="text-gray-400 hover:text-blue-500 p-1.5 rounded-md hover:bg-blue-50 transition-colors" title="编辑">
                        <i class="fa-solid fa-pen"></i>
                    </button>
                    <button onclick="deleteAgent('${item.id}')" class="text-gray-400 hover:text-red-500 p-1.5 rounded-md hover:bg-red-50 transition-colors" title="删除">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>
            </div>
            <h3 class="text-lg font-bold text-gray-900 mb-2 truncate">${escapeHtml(item.name)}</h3>
            <p class="text-gray-500 text-sm mb-3 line-clamp-2 h-10">${escapeHtml(item.description || '暂无描述')}</p>
            
            <div class="mb-3 h-6 overflow-hidden">
                 ${kbBadges || '<span class="text-xs text-gray-400">未关联知识库</span>'}
            </div>

            <div class="flex items-center justify-between text-xs text-gray-400 pt-4 border-t border-gray-50">
                <span class="bg-gray-100 px-2 py-1 rounded text-gray-500">${item.model_name}</span>
                <span>${formatDate(item.created_at)}</span>
            </div>
        `;
        grid.appendChild(card);
    });
}

function renderKBSelection(selectedIds = []) {
    const container = document.getElementById('kbListContainer');
    if (availableKBs.length === 0) {
        container.innerHTML = '<p class="text-sm text-gray-400 text-center py-2">暂无可用知识库</p>';
        return;
    }

    container.innerHTML = availableKBs.map(kb => `
        <div class="flex items-center p-2 hover:bg-gray-100 rounded">
            <input type="checkbox" id="kb_${kb.id}" name="kb_ids" value="${kb.id}" 
                ${selectedIds.includes(kb.id) ? 'checked' : ''}
                class="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded">
            <label for="kb_${kb.id}" class="ml-2 block text-sm text-gray-900 cursor-pointer flex-1">
                ${escapeHtml(kb.name)}
            </label>
        </div>
    `).join('');
}

// --- Actions ---
async function handleSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const btn = form.querySelector('button[type="submit"]');
    const spinner = document.getElementById('submitBtnSpinner');
    const btnText = document.getElementById('submitBtnText');
    const agentId = document.getElementById('agentId').value;
    const isEdit = !!agentId;

    const selectedKBs = Array.from(form.querySelectorAll('input[name="kb_ids"]:checked')).map(cb => cb.value);

    btn.disabled = true;
    spinner.classList.remove('hidden');
    btnText.textContent = isEdit ? '保存中...' : '创建中...';

    const payload = {
        name: form.name.value,
        description: form.description.value,
        prompt: form.prompt.value,
        tenant_id: TENANT_ID,
        kb_ids: selectedKBs
    };

    try {
        let url = '/agent/agents';
        let method = 'POST';

        if (isEdit) {
            url = `/agent/agents/${agentId}?tenant_id=${TENANT_ID}`;
            method = 'PUT';
        }

        await apiFetch(url, {
            method: method,
            body: payload
        });
        
        showToast(isEdit ? '智能体已更新' : '智能体创建成功');
        closeModal();
        fetchAgents();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btn.disabled = false;
        spinner.classList.add('hidden');
        btnText.textContent = isEdit ? '保存' : '创建';
    }
}

async function deleteAgent(id) {
    if (!confirm('确定要删除这个智能体吗？')) return;

    try {
        await apiFetch(`/agent/agents/${id}?tenant_id=${TENANT_ID}`, {
            method: 'DELETE'
        });
        
        showToast('智能体已删除');
        fetchAgents();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// --- UI Helpers ---
function openCreateModal() {
    document.getElementById('modal').classList.remove('hidden');
    document.getElementById('modalTitle').textContent = '新建智能体';
    document.getElementById('submitBtnText').textContent = '创建';
    document.getElementById('agentForm').reset();
    document.getElementById('agentId').value = '';
    renderKBSelection([]);
}

function openEditModal(id) {
    const agent = currentAgents.find(a => a.id === id);
    if (!agent) return;

    document.getElementById('modal').classList.remove('hidden');
    document.getElementById('modalTitle').textContent = '编辑智能体';
    document.getElementById('submitBtnText').textContent = '保存';
    
    document.getElementById('agentId').value = agent.id;
    document.getElementById('nameInput').value = agent.name;
    document.getElementById('descInput').value = agent.description || '';
    document.getElementById('promptInput').value = agent.prompt || '';
    
    const selectedIds = agent.knowledge_bases.map(kb => kb.id);
    renderKBSelection(selectedIds);
}

function closeModal() {
    document.getElementById('modal').classList.add('hidden');
}
