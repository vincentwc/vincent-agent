const API_BASE = window.location.origin;
const TENANT_ID = "default_tenant";

async function apiFetch(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const defaultHeaders = {
        'Content-Type': 'application/json'
    };

    if (options.body && !(options.body instanceof FormData)) {
        options.headers = { ...defaultHeaders, ...options.headers };
        options.body = JSON.stringify(options.body);
    }

    try {
        const response = await fetch(url, options);
        const json = await response.json();

        if (!response.ok || (json.code !== undefined && json.code !== 200)) {
            throw new Error(json.message || `Request failed with status ${response.status}`);
        }

        return json.data || json;
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        throw error;
    }
}
