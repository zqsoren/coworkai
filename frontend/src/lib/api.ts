import axios from 'axios';
// HMR Trigger: V2 File System

const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000/api' : '/api');

console.log('[API] API_BASE_URL:', API_BASE_URL);

export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 120000,
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
    console.log('[API] Request interceptor - URL:', config.baseURL + (config.url || ''));
    const token = localStorage.getItem('auth_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    response => response,
    error => {
        if (error.response?.status === 401) {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth_user');
            window.dispatchEvent(new Event('auth_show_login'));
        }
        console.error("[API Error]", error.response?.data || error.message);
        return Promise.reject(error);
    }
);

export interface Workspace {
    id: string;
    name: string;
}

export interface Agent {
    id: string;
    name: string;
    system_prompt: string; // The main description/role
    workspace: string;
    // Optional details for editing
    provider_id?: string;
    model_name?: string;
    persona_mode?: string; // normal | efficient | concise
    tools?: string[];
    skills?: string[];
}

export interface ChatResponse {
    response: string;
    messages: Array<{ role: string; content: string }>;
    pending_changes: Array<any>;
    status?: 'CONTINUE' | 'FINISH'; // For multi-turn orchestration
    current_plan?: any; // For Plan Visualization in Right Panel
}

export const fetchWorkspaces = async (): Promise<Workspace[]> => {
    const response = await api.get('/workspaces');
    return response.data;
};

export const fetchAgents = async (workspaceId?: string): Promise<Agent[]> => {
    const response = await api.get('/agents', {
        params: { workspace_id: workspaceId },
    });
    return response.data;
};

export const sendMessage = async (
    workspaceId: string,
    agentId: string,
    message: string,
    groupId?: string
): Promise<ChatResponse> => {
    // If groupId is present, use group chat endpoint
    if (groupId) {
        return api.post('/group/chat', {
            workspace_id: workspaceId,
            group_id: groupId,
            message: message
        }).then(res => res.data);
    }

    const response = await api.post('/chat/invoke', {
        message,
        agent_id: agentId,
        workspace_id: workspaceId,
    });
    return response.data;
};

export const readFile = async (filePath: string): Promise<{ content: string; file_path: string }> => {
    const response = await api.post('/file/read', { file_path: filePath });
    return response.data;
};

// --- Agent Management ---
export const createAgent = async (
    workspaceId: string,
    name: string,
    systemPrompt: string,
    providerId: string,
    modelName: string
): Promise<{ status: string; agent_id: string }> => {
    const response = await api.post('/agent/create', {
        workspace_id: workspaceId,
        name,
        system_prompt: systemPrompt,
        provider_id: providerId,
        model_name: modelName,
    });
    return response.data;
};

export const updateAgent = async (
    workspaceId: string,
    agentId: string,
    updates: any
): Promise<void> => {
    // updates: { name?, system_prompt?, provider_id?, model_name? }
    await api.post('/agent/update', {
        workspace_id: workspaceId,
        agent_id: agentId,
        ...updates
    });
};

export const deleteAgent = async (agentId: string): Promise<void> => {
    await api.delete(`/agent/delete/${agentId}`);
};

// --- Workspace Management ---
export const createWorkspace = async (name: string): Promise<{ status: string; workspace_id: string }> => {
    const response = await api.post('/workspace/create', { name });
    return response.data;
};

export const renameWorkspace = async (workspaceId: string, newName: string): Promise<void> => {
    await api.post('/workspace/rename', { workspace_id: workspaceId, new_name: newName });
};

export const deleteWorkspace = async (workspaceId: string): Promise<void> => {
    await api.delete(`/workspace/delete/${workspaceId}`);
};

// --- Settings (Providers) ---
export interface LLMProvider {
    id: string;
    type: string;
    name: string;
    models: string[];
    base_url?: string;
    api_key_env: string;
    is_builtin?: boolean;
}

export const fetchProviders = async (): Promise<LLMProvider[]> => {
    const response = await api.get('/settings/providers');
    return response.data;
};

export const fetchSkills = async (): Promise<any[]> => {
    const response = await api.get('/skills');
    return response.data;
};

export const fetchTools = async (): Promise<any[]> => {
    const response = await api.get('/tools');
    return response.data;
};

export const summarizeBasket = async (fragments: string[], workspace_id?: string, group_id?: string, agent_id?: string, user_instruction?: string): Promise<string> => {
    const response = await api.post('/util/summarize', { fragments, workspace_id, group_id, agent_id, user_instruction }, {
        timeout: 300000 // 5 minutes timeout for LLM
    });
    return response.data.summary;
};

export const testConnectivity = async (): Promise<boolean> => {
    try {
        const response = await api.get('/util/test');
        return response.data.status === 'ok';
    } catch {
        return false;
    }
};

export const saveProvider = async (provider: LLMProvider): Promise<void> => {
    await api.post('/settings/provider', provider);
};

export const clearGroupMessages = async (workspaceId: string, groupId: string): Promise<void> => {
    await api.post(`/group/${groupId}/clear`, null, { params: { workspace_id: workspaceId } });
};

export const deleteProvider = async (providerId: string): Promise<void> => {
    await api.delete(`/settings/provider/${providerId}`);
};

export const fetchAllModels = async (): Promise<Array<{ provider_id: string; model_name: string; display: string }>> => {
    const response = await api.get('/settings/models');
    return response.data;
};

export const uploadWorkspaceFiles = async (
    path: string,
    files: File[]
): Promise<void> => {
    const formData = new FormData();
    formData.append('path', path);
    files.forEach((file) => formData.append('files', file));

    await api.post('/files/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
};

// --- Knowledge Base & Files ---
export const fetchFiles = async (workspaceId: string, agentId: string, type: string): Promise<{ files: string[] }> => {
    // type: 'knowledge_base' | 'context/static' | 'context/active' | 'context/archives'
    const response = await api.get('/knowledge/files', {
        params: { workspace_id: workspaceId, agent_id: agentId, type },
    });
    return response.data;
};

export const uploadFiles = async (
    workspaceId: string,
    agentId: string,
    type: string,
    files: File[]
): Promise<void> => {
    const formData = new FormData();
    formData.append('workspace_id', workspaceId);
    formData.append('agent_id', agentId);
    formData.append('type', type);
    files.forEach((file) => formData.append('files', file));

    await api.post('/knowledge/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
};

export const processKnowledgeBase = async (workspaceId: string, agentId: string): Promise<any> => {
    const response = await api.post('/knowledge/process', {
        workspace_id: workspaceId,
        agent_id: agentId,
    });
    return response.data;
};

export const deleteFile = async (workspaceId: string, agentId: string, type: string, filename: string): Promise<void> => {
    await api.delete('/knowledge/file', {
        params: { workspace_id: workspaceId, agent_id: agentId, type, filename },
    });
};

// --- System / Changes ---
export const applyChange = async (
    file_path: string,
    original_content: string,
    new_content: string,
    diff_lines: string[]
): Promise<void> => {
    await api.post('/sys/change/apply', {
        file_path,
        original_content,
        new_content,
        diff_lines,
        status: "approved"
    });
};

// --- Group Chat Management ---
export interface GroupChat {
    id: string;
    name: string;
    members: string[];
    supervisor_id: string;
    supervisor_prompt?: string;
    workflow_supervisor_prompt?: string;
}

export const fetchGroups = async (workspaceId: string): Promise<GroupChat[]> => {
    const response = await api.get('/group/list', { params: { workspace_id: workspaceId } });
    return response.data;
};

export const createGroup = async (workspaceId: string, name: string, memberIds: string[], supervisorId: string): Promise<GroupChat> => {
    const response = await api.post('/group/create', {
        workspace_id: workspaceId,
        name,
        member_agent_ids: memberIds,
        supervisor_id: supervisorId
    });
    return response.data;
};

export const updateGroup = async (workspaceId: string, groupId: string, updates: { supervisor_id?: string; supervisor_prompt?: string; name?: string; members?: string[] }): Promise<GroupChat> => {
    const response = await api.post('/group/update', {
        workspace_id: workspaceId,
        group_id: groupId,
        ...updates
    });
    return response.data;
};

export const deleteGroup = async (workspaceId: string, groupId: string): Promise<void> => {
    await api.delete(`/group/delete/${groupId}`, { params: { workspace_id: workspaceId } });
};

export const sendGroupMessage = async (
    workspaceId: string,
    groupId: string,
    message: string,
    history: any[]
): Promise<{ response: string; speaker: string; history: any[]; status: string }> => {
    const response = await api.post('/group/chat', {
        workspace_id: workspaceId,
        group_id: groupId,
        message,
        history
    });
    return response.data;
};

// Workflow Mode APIs
export const generateWorkflowPlan = async (
    workspaceId: string,
    groupId: string,
    userRequest: string
): Promise<{ workflow: any; status: string }> => {
    const response = await api.post('/group/plan', {
        workspace_id: workspaceId,
        group_id: groupId,
        user_request: userRequest
    });
    return response.data;
};

export const executeWorkflowPlan = async (
    workspaceId: string,
    groupId: string,
    workflow: any,
    history: any[]
): Promise<{ history: any[]; status: string }> => {
    const response = await api.post('/group/execute', {
        workspace_id: workspaceId,
        group_id: groupId,
        workflow,
        history
    });
    return response.data;
};



export const fetchGroupMessages = async (workspaceId: string, groupId: string, limit: number = 100) => {
    const response = await api.get(`/group/${groupId}/messages`, {
        params: { workspace_id: workspaceId, limit }
    });
    return response.data;
};

// --- File System V2 ---

export interface FileNode {
    name: string;
    path: string; // relative to data_root
    is_dir: boolean;
    locked: boolean;
    children: FileNode[];
}

export const fetchFileTree = async (workspaceId: string, agentId?: string, rootType: 'shared' | 'private' | 'archives' = 'shared'): Promise<FileNode[]> => {
    const response = await api.get('/files/tree', {
        params: { workspace_id: workspaceId, agent_id: agentId, root_type: rootType }
    });
    return response.data;
};

export const setFileLock = async (path: string, locked: boolean): Promise<void> => {
    await api.post('/files/lock', { path, locked });
};

export const createDirectory = async (path: string): Promise<void> => {
    await api.post('/files/mkdir', { path });
};

export const renameFileItem = async (oldPath: string, newPath: string): Promise<void> => {
    await api.post('/files/rename', { old_path: oldPath, new_path: newPath });
};

export const deleteFileItem = async (path: string): Promise<void> => {
    await api.delete('/files/delete', {
        data: { path }
    });
};

export const fetchFileContent = async (path: string): Promise<{ path: string; content: string }> => {
    const response = await api.get('/files/content', { params: { path } });
    return response.data;
};

export const saveFileContent = async (path: string, content: string): Promise<void> => {
    await api.post('/files/content', { path, content });
};

// --- Feishu Bot ---
export const registerFeishu = async (appId: string, appSecret: string, agentId: string, workspaceId: string): Promise<{ status: string; id: string }> => {
    const response = await api.post('/feishu/register', { app_id: appId, app_secret: appSecret, agent_id: agentId, workspace_id: workspaceId });
    return response.data;
};

export const unregisterFeishu = async (appId: string): Promise<void> => {
    await api.delete('/feishu/unregister', { params: { app_id: appId } });
};

// --- Output Modes ---

export interface OutputMode {
    id: string;
    name: string;
    description: string;
    prompt: string;
    is_builtin: boolean;
}

export const fetchOutputModes = async (): Promise<OutputMode[]> => {
    const response = await api.get('/output-modes');
    return response.data;
};

export const createOutputMode = async (mode: { name: string; description?: string; prompt: string }): Promise<OutputMode> => {
    const response = await api.post('/output-modes', mode);
    return response.data;
};

export const updateOutputMode = async (id: string, mode: { name?: string; description?: string; prompt?: string }): Promise<OutputMode> => {
    const response = await api.put(`/output-modes/${id}`, mode);
    return response.data;
};

export const deleteOutputMode = async (id: string): Promise<void> => {
    await api.delete(`/output-modes/${id}`);
};

// ============================================================
// Auth API
// ============================================================

export interface AuthUser {
    id: string;
    username: string;
    phone: string;
}

export interface AuthResponse {
    token: string;
    user: AuthUser;
}

export const authRegister = async (username: string, phone: string, password: string): Promise<AuthResponse> => {
    const response = await api.post('/auth/register', { username, phone, password });
    return response.data;
};

export const authLogin = async (phone: string, password: string): Promise<AuthResponse> => {
    console.log('[API] authLogin called, baseURL:', API_BASE_URL);
    console.log('[API] Sending request to /auth/login');
    try {
        const response = await api.post('/auth/login', { phone, password });
        console.log('[API] authLogin response:', response);
        return response.data;
    } catch (error) {
        console.error('[API] authLogin error:', error);
        throw error;
    }
};

export const authGetMe = async (): Promise<AuthUser> => {
    const response = await api.get('/auth/me');
    return response.data;
};

// ============================================================
// Market API
// ============================================================

export interface MarketAgent {
    id: string;
    name: string;
    description: string;
    system_prompt: string;
    tools: string[];
    skills: string[];
    mcp_servers: any[];
    knowledge_base: string[];
    publisher_id: string;
    published_at: string;
    downloads: number;
    rating: number;
}

export const fetchMarketAgents = async (): Promise<MarketAgent[]> => {
    const response = await api.get('/market/agents');
    return response.data;
};

export const publishAgentToMarket = async (data: {
    name: string;
    system_prompt: string;
    description?: string;
    tools?: string[];
    skills?: string[];
    mcp_servers?: any[];
    knowledge_base?: string[];
}): Promise<{ status: string; market_agent_id: string }> => {
    const response = await api.post('/market/publish', data);
    return response.data;
};

export const importMarketAgent = async (
    marketAgentId: string,
    targetWorkspaceId: string
): Promise<{ status: string; agent_id: string }> => {
    const response = await api.post('/market/import', {
        market_agent_id: marketAgentId,
        target_workspace_id: targetWorkspaceId,
    });
    return response.data;
};

// ============================================================
// Scheduled Tasks API
// ============================================================

export interface ScheduledTask {
    id: string;
    agent_id: string;
    workspace_id: string;
    user_id: string;
    mode: 'calendar' | 'interval';
    scope?: string;
    calendar_unit?: string;
    time?: string;
    day_of_week?: string;
    day_of_month?: number;
    work_start?: string;
    work_end?: string;
    interval_value?: number;
    interval_unit?: string;
    prompt: string;
    enabled: boolean;
    last_run?: string | null;
    last_status?: string | null;
    created_at: string;
}

export const fetchScheduledTasks = async (agentId: string): Promise<ScheduledTask[]> => {
    const response = await api.get('/schedule/list', { params: { agent_id: agentId } });
    return response.data;
};

export const createScheduledTask = async (task: Omit<ScheduledTask, 'id' | 'user_id' | 'last_run' | 'last_status' | 'created_at'>): Promise<{ status: string; task_id: string }> => {
    const response = await api.post('/schedule/create', task);
    return response.data;
};

export const updateScheduledTask = async (taskId: string, updates: Partial<ScheduledTask>): Promise<void> => {
    await api.post('/schedule/update', { task_id: taskId, ...updates });
};

export const deleteScheduledTask = async (taskId: string): Promise<void> => {
    await api.delete(`/schedule/delete/${taskId}`);
};

// Inbox API
export interface InboxMessage {
    id: string;
    task_id: string;
    timestamp: string;
    prompt: string;
    response: string;
    read: boolean;
}

export const fetchInbox = async (agentId: string): Promise<InboxMessage[]> => {
    const response = await api.get('/schedule/inbox', { params: { agent_id: agentId } });
    return response.data;
};

export const markInboxRead = async (agentId: string): Promise<void> => {
    await api.post('/schedule/inbox/mark-read', null, { params: { agent_id: agentId } });
};

export const fetchUnreadAgents = async (): Promise<string[]> => {
    const response = await api.get('/schedule/inbox/unread-agents');
    return response.data;
};

