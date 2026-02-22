import { create } from 'zustand';
import { fetchWorkspaces, fetchAgents, sendMessage, createAgent, fetchProviders, saveProvider, deleteProvider, fetchFiles, uploadFiles, deleteFile, processKnowledgeBase, updateAgent, applyChange, fetchGroupMessages } from './lib/api';
import type { Workspace, Agent, LLMProvider, GroupChat } from './lib/api';
import { sessionManager } from './utils/sessionManager';

interface Message {
    role: 'user' | 'assistant' | 'system';
    content: string;
    name?: string; // Speaker name for group chat
    shouldAnimate?: boolean;
    is_plan?: boolean;
    is_basket_summary?: boolean;
}

export interface ActivityEvent {
    id: string;
    type: 'thinking' | 'tool_call' | 'tool_result' | 'done' | 'error';
    agentName: string;
    toolName?: string;
    args?: string;
    result?: string;
    timestamp: number;
}
export interface ChangeRequest {
    file_path: string;
    original_content: string;
    new_content: string;
    diff_lines: string[];
    status: string;
    created_at: string;
    comment: string;
}

interface AppState {
    // Auth
    user: { id: string; username: string; phone: string } | null;
    token: string | null;
    isAuthenticated: boolean;
    showLoginModal: boolean;

    language: 'en' | 'zh';
    workspaces: Workspace[];
    currentWorkspaceId: string | null;
    agents: Agent[];
    currentAgentId: string | null;

    // Groups
    groups: GroupChat[];
    currentGroupId: string | null;

    agentConfig: Agent | null;
    messages: Message[];
    pendingChanges: ChangeRequest[];
    isRightPanelOpen: boolean;
    isLoading: boolean;

    // Activity Log (real-time agent steps)
    activityLog: ActivityEvent[];
    activeAgents: string[];

    // Workflow Mode
    pendingWorkflow: any | null; // Workflow plan waiting for user approval
    approvedWorkflows: any[]; // [NEW] History of approved/executed workflows
    workflowMode: boolean; // Whether workflow mode is enabled
    chatMode: 'workflow' | 'legacy'; // Current chat mode for group chats

    chatHistory: Record<string, Message[]>; // agentId -> messages

    // Group Messages (New)
    groupMessages: Record<string, Message[]>; // groupId -> messages

    // Session History
    currentSessionId: string | null;

    // Actions
    setLanguage: (lang: 'en' | 'zh') => void;
    setWorkspaces: (workspaces: Workspace[]) => void;
    setCurrentWorkspaceId: (id: string) => Promise<void>;
    setAgents: (agents: Agent[]) => void;
    setCurrentAgentId: (id: string) => void;

    setGroups: (groups: GroupChat[]) => void;
    setCurrentGroupId: (id: string | null) => void;
    loadGroups: (workspaceId: string) => Promise<void>;
    createGroup: (name: string, members: string[], supervisorId: string) => Promise<void>;
    updateGroupSettings: (groupId: string, updates: any) => Promise<void>;

    addMessage: (message: Message) => void;
    setMessages: (messages: Message[]) => void;
    setPendingChanges: (changes: ChangeRequest[]) => void;
    toggleRightPanel: () => void;
    setIsLoading: (isLoading: boolean) => void;
    sendChatMessage: (text: string) => Promise<void>;

    // Group Message Actions
    loadGroupMessages: (groupId: string) => Promise<void>;
    addGroupMessage: (groupId: string, message: Message) => void;

    // Activity Log Actions
    pushActivity: (event: ActivityEvent) => void;
    clearActivity: () => void;

    // Workflow Mode Actions
    generateWorkflowPlan: (userRequest: string) => Promise<void>;
    executeWorkflow: () => Promise<void>;
    cancelWorkflow: () => void;

    loadWorkspaces: () => Promise<void>;
    loadAgents: (workspaceId: string) => Promise<void>;

    // --- New Actions ---
    fetchProviders: () => Promise<void>;
    saveProvider: (provider: LLMProvider) => Promise<void>;
    deleteProvider: (providerId: string) => Promise<void>;

    createAgent: (name: string, systemPrompt: string, providerId: string, modelName: string) => Promise<string>;
    updateAgent: (agentId: string, updates: any) => Promise<void>;
    deleteAgent: (agentId: string) => Promise<void>;

    createWorkspace: (name: string) => Promise<void>;
    renameWorkspace: (workspaceId: string, newName: string) => Promise<void>;
    deleteWorkspace: (workspaceId: string) => Promise<void>;

    applyChange: (change: ChangeRequest) => Promise<void>;

    listFiles: (type: string) => Promise<string[]>;
    uploadFiles: (type: string, files: File[]) => Promise<void>;
    deleteFile: (type: string, filename: string) => Promise<void>;
    processKnowledge: () => Promise<any>;

    // New: Explicitly set pending workflow for Legacy Mode visualization
    setPendingWorkflow: (workflow: any) => void;

    // Chat Mode
    setChatMode: (mode: 'workflow' | 'legacy') => void;

    // Session History
    startNewSession: () => void;
    switchSession: (sessionId: string) => void;

    // Auth Actions
    setAuth: (token: string, user: { id: string; username: string; phone: string }) => void;
    logout: () => void;
    initAuth: () => void;
    openLoginModal: () => void;
    closeLoginModal: () => void;
    requireAuth: (callback?: () => void) => boolean;
}

export const useStore = create<AppState>((set, get) => ({
    // Auth
    user: null,
    token: localStorage.getItem('auth_token'),
    isAuthenticated: !!localStorage.getItem('auth_token'),
    showLoginModal: false,

    language: 'en',
    workspaces: [],
    currentWorkspaceId: null,
    agents: [],
    currentAgentId: null,

    groups: [],
    currentGroupId: null,

    agentConfig: null,
    messages: [],
    chatHistory: {},
    groupMessages: {},
    pendingChanges: [],
    isRightPanelOpen: true,
    isLoading: false,

    activityLog: [],
    activeAgents: [],

    // Workflow Mode初始值
    pendingWorkflow: null,
    approvedWorkflows: [], // [NEW] History
    workflowMode: false, // Default to false (legacy mode)
    chatMode: 'legacy', // Default to legacy mode

    // Session History
    currentSessionId: null,

    setLanguage: (lang) => set({ language: lang }),
    setWorkspaces: (workspaces) => set({ workspaces }),
    setCurrentWorkspaceId: async (id) => {
        set({
            currentWorkspaceId: id,
            isLoading: true,
            agents: [],
            groups: [],
            currentAgentId: null,
            currentGroupId: null,
            messages: []
        });

        try {
            await get().loadAgents(id);
            await get().loadGroups(id);
        } catch (error) {
            console.error('Failed to switch workspace:', error);
        } finally {
            set({ isLoading: false });
        }
    },
    setAgents: (agents) => set({ agents }),

    setCurrentAgentId: (id) => set((state) => {
        // Auto-save current session before switching if it has messages
        const prevContextId = state.currentAgentId || state.currentGroupId;
        if (prevContextId && state.currentSessionId && state.messages.length > 0) {
            sessionManager.saveSession(prevContextId, state.currentSessionId, state.messages);
        }

        // Just switch agent, don't force a new session ID unless needed
        return {
            currentAgentId: id,
            currentGroupId: null,
            messages: state.chatHistory[id] || [],
            // If the target agent doesn't have a session ID yet, generate one
            currentSessionId: state.currentSessionId || sessionManager.generateSessionId()
        };
    }),

    addMessage: (message) => set((state) => {
        const key = state.currentAgentId || state.currentGroupId;
        if (!key) return state;

        // Mark new messages for animation
        const messageWithAnim = { ...message, shouldAnimate: true };
        const newMessages = [...state.messages, messageWithAnim];

        // Auto-save session to localStorage
        const sessionId = state.currentSessionId || sessionManager.generateSessionId();
        setTimeout(() => sessionManager.saveSession(key, sessionId, newMessages), 0);

        return {
            messages: newMessages,
            chatHistory: {
                ...state.chatHistory,
                [key]: newMessages
            },
            currentSessionId: sessionId
        };
    }),

    setMessages: (messages) => set((state) => {
        const key = state.currentAgentId || state.currentGroupId;
        if (!key) return { messages };

        return {
            messages,
            chatHistory: {
                ...state.chatHistory,
                [key]: messages
            }
        };
    }),

    setPendingChanges: (changes) => set({ pendingChanges: changes }),
    toggleRightPanel: () => set((state) => ({ isRightPanelOpen: !state.isRightPanelOpen })),
    setIsLoading: (isLoading) => set({ isLoading }),

    // Chat Mode
    setChatMode: (mode) => set({ chatMode: mode }),

    loadWorkspaces: async () => {
        try {
            const workspaces = await fetchWorkspaces();
            set({ workspaces });
            if (workspaces.length > 0 && !get().currentWorkspaceId) {
                set({ currentWorkspaceId: workspaces[0].id });
                // Load agents for the first workspace
                await get().loadAgents(workspaces[0].id);
                await get().loadGroups(workspaces[0].id);
            }
        } catch (error) {
            console.error('Failed to load workspaces:', error);
        }
    },

    loadAgents: async (workspaceId) => {
        try {
            let agents = await fetchAgents(workspaceId);
            const metaAgent: Agent = {
                id: "meta_agent",
                name: "超级助手",
                workspace: "workspace_default",
                system_prompt: "你是系统的超级助手 (Meta Agent)，负责监督和管理整个工作区。\n你可以使用工具协助用户分析现状、搜集信息，或通过 create_new_agent 工具帮用户规划和创建新的 Agent。",
                provider_id: "builtin_glm4air_free",
                model_name: "z-ai/glm-4.5-air:free",
                tools: ["create_new_agent", "list_available_agents", "list_all_files", "read_any_file", "search_files_by_keyword", "suggest_delegation_to_agent", "read_file", "write_file", "google_search"],
                skills: []
            } as Agent;
            agents = [metaAgent, ...agents];

            set({ agents });
            if (agents.length > 0) {
                const currentId = get().currentAgentId;
                const stillExists = currentId && agents.find(a => a.id === currentId);

                if (!stillExists) {
                    const firstAgentId = agents[0].id;
                    set((state) => ({
                        currentAgentId: firstAgentId,
                        messages: state.chatHistory[firstAgentId] || []
                    }));
                }
                // If still exists, do nothing (keep current selection)
            } else {
                set({ currentAgentId: null, messages: [] });
            }
        } catch (error) {
            console.error('Failed to load agents:', error);
            set({ agents: [], currentAgentId: null });
        }
    },

    setGroups: (groups) => set({ groups }),
    setCurrentGroupId: (id) => set((state) => {
        // Auto-save current session before switching
        const prevContextId = state.currentAgentId || state.currentGroupId;
        if (prevContextId && state.currentSessionId && state.messages.length > 0) {
            sessionManager.saveSession(prevContextId, state.currentSessionId, state.messages);
        }
        const newSessionId = id ? sessionManager.generateSessionId() : null;
        return {
            currentGroupId: id,
            currentAgentId: null,
            messages: id ? (state.chatHistory[id] || []) : [],
            currentSessionId: newSessionId
        };
    }),
    loadGroups: async (workspaceId) => {
        const { fetchGroups } = await import('./lib/api');
        const groups = await fetchGroups(workspaceId);
        set({ groups });
    },
    createGroup: async (name, members, supervisorId) => {
        const { createGroup } = await import('./lib/api');
        const { currentWorkspaceId, loadGroups } = get();
        if (!currentWorkspaceId) return;
        await createGroup(currentWorkspaceId, name, members, supervisorId);
        await loadGroups(currentWorkspaceId);
    },
    updateGroupSettings: async (groupId, updates) => {
        const { updateGroup } = await import('./lib/api');
        const { currentWorkspaceId, loadGroups } = get();
        if (!currentWorkspaceId) return;
        await updateGroup(currentWorkspaceId, groupId, updates);
        await loadGroups(currentWorkspaceId);
    },

    sendChatMessage: async (text: string) => {
        const { currentAgentId, currentGroupId, currentWorkspaceId, chatMode } = get();
        if (!currentWorkspaceId) return;

        // Group Chat Logic
        if (currentGroupId) {
            // Optimistic update
            const newMessage: Message = { role: 'user', content: text };
            get().addGroupMessage(currentGroupId, newMessage);

            try {
                if (chatMode === 'workflow') {
                    // Workflow Mode: Use new plan/execute flow?
                    // For now, let's stick to legacy chat endpoint but maybe update it later.
                    const { sendMessage } = await import('./lib/api');
                    await sendMessage(currentWorkspaceId, currentAgentId || '', text, currentGroupId);

                    // After sending, refresh messages
                    setTimeout(() => {
                        get().loadGroupMessages(currentGroupId);
                    }, 1000);

                } else {
                    // Legacy Mode: use SSE streaming endpoint
                    const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000/api' : '/api');

                    const runStep = async (msg: string, turnCount: number): Promise<void> => {
                        if (turnCount > 10) { console.warn('Max auto-turns reached.'); return; }

                        // Clear previous activity before each step
                        get().clearActivity();

                        const token = localStorage.getItem('auth_token');
                        const res = await fetch(`${API_BASE_URL}/group/chat/stream`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                            },
                            body: JSON.stringify({
                                workspace_id: currentWorkspaceId,
                                group_id: currentGroupId,
                                message: msg,
                                history: []
                            })
                        });

                        if (!res.ok || !res.body) {
                            console.error('[GroupChat] Stream request failed:', res.status, res.statusText);
                            get().clearActivity();
                            return;
                        }
                        console.log('[GroupChat SSE] Connected, reading stream...');

                        const reader = res.body.getReader();
                        const decoder = new TextDecoder();
                        let buffer = '';
                        let shouldContinue = false;

                        while (true) {
                            const { done, value } = await reader.read();
                            if (done) break;
                            buffer += decoder.decode(value, { stream: true });
                            const blocks = buffer.split('\n\n');
                            buffer = blocks.pop() || '';

                            for (const block of blocks) {
                                if (!block.trim()) continue;
                                const eventMatch = block.match(/^event: (.*)$/m);
                                const dataMatch = block.match(/^data: (.*)$/m);
                                if (!eventMatch || !dataMatch) continue;

                                const eventType = eventMatch[1].trim();
                                let data: any = {};
                                try { data = JSON.parse(dataMatch[1].trim()); } catch { continue; }

                                console.log('[GroupChat SSE] Event:', eventType, data);

                                if (eventType === 'thinking') {
                                    get().pushActivity({
                                        id: `${data.agent}-thinking-${Date.now()}`,
                                        type: 'thinking', agentName: data.agent, timestamp: Date.now()
                                    });
                                } else if (eventType === 'tool_call') {
                                    get().pushActivity({
                                        id: `${data.agent}-tool-${data.tool}-${Date.now()}`,
                                        type: 'tool_call', agentName: data.agent,
                                        toolName: data.tool, args: data.args, timestamp: Date.now()
                                    });
                                } else if (eventType === 'tool_result') {
                                    get().pushActivity({
                                        id: `${data.agent}-result-${data.tool}-${Date.now()}`,
                                        type: 'tool_result', agentName: data.agent,
                                        toolName: data.tool, result: data.result, timestamp: Date.now()
                                    });
                                } else if (eventType === 'agent_message') {
                                    // Final message – reload from backend and clear activity
                                    get().loadGroupMessages(currentGroupId);
                                } else if (eventType === 'plan') {
                                    console.log('[GroupChat SSE] Plan received:', data.data);
                                    if (data.data) get().setPendingWorkflow(data.data);
                                } else if (eventType === 'finish') {
                                    shouldContinue = data.status === 'CONTINUE';
                                    get().clearActivity();
                                    get().loadGroupMessages(currentGroupId);
                                } else if (eventType === 'error') {
                                    console.error('[GroupChat] SSE error:', data.content);
                                    get().clearActivity();
                                }
                            }
                        }

                        if (shouldContinue) {
                            setTimeout(() => runStep('', turnCount + 1), 2000);
                        }
                    };

                    await runStep(text, 1);
                }
            } catch (error) {
                console.error("Failed to send group message:", error);
            }
            return;
        }

        // Single Agent Chat Logic
        if (!currentAgentId) return;

        const newMessage: Message = { role: 'user', content: text };
        set((state) => ({
            chatHistory: {
                ...state.chatHistory,
                [currentAgentId]: [...(state.chatHistory[currentAgentId] || []), newMessage]
            },
            messages: [...(state.chatHistory[currentAgentId] || []), newMessage] // Update current view
        }));

        try {
            const response = await sendMessage(currentWorkspaceId, currentAgentId, text);
            const aiMessage: Message = { role: 'assistant', content: response.response, shouldAnimate: true };

            set((state) => ({
                chatHistory: {
                    ...state.chatHistory,
                    [currentAgentId]: [...(state.chatHistory[currentAgentId] || []), aiMessage]
                },
                messages: [...(state.chatHistory[currentAgentId] || []), aiMessage]
            }));

            // Auto-save session after AI response
            const finalState = get();
            if (finalState.currentSessionId) {
                sessionManager.saveSession(currentAgentId, finalState.currentSessionId, finalState.messages);
            }
        } catch (error) {
            console.error(error);
        }
    },

    // --- Group Message Actions Implementation ---

    loadGroupMessages: async (groupId: string) => {
        const { currentWorkspaceId } = get();
        if (!currentWorkspaceId) return;
        try {
            const data = await fetchGroupMessages(currentWorkspaceId, groupId);
            set((state) => ({
                groupMessages: {
                    ...state.groupMessages,
                    [groupId]: data.messages || []
                }
            }));
        } catch (error) {
            console.error("Failed to load group messages:", error);
        }
    },

    addGroupMessage: (groupId: string, message: Message) => {
        set((state) => ({
            groupMessages: {
                ...state.groupMessages,
                [groupId]: [...(state.groupMessages[groupId] || []), message]
            }
        }));
    },

    pushActivity: (event: ActivityEvent) => set((state) => {
        const exists = state.activityLog.some(e => e.id === event.id);
        if (exists) return state;
        const agentName = event.agentName;
        const isAlreadyActive = state.activeAgents.includes(agentName);
        return {
            activityLog: [...state.activityLog, event],
            activeAgents: isAlreadyActive ? state.activeAgents : [...state.activeAgents, agentName],
        };
    }),

    clearActivity: () => set({ activityLog: [], activeAgents: [] }),

    // --- New Implementations ---
    fetchProviders: async () => {
        return await fetchProviders().then(() => { }); // wrapper if we needed state, but mostly consumed directly
    },
    saveProvider: async (provider) => {
        await saveProvider(provider);
    },
    deleteProvider: async (id) => {
        await deleteProvider(id);
    },
    createAgent: async (name, systemPrompt, pid, model) => {
        const { currentWorkspaceId, loadAgents } = get();
        if (!currentWorkspaceId) throw new Error("No workspace selected");

        // Pass systemPrompt as the roleDesc argument to API, or update API?
        // Let's assume api.createAgent signature needs update too.
        const res = await createAgent(currentWorkspaceId, name, systemPrompt, pid, model);
        await loadAgents(currentWorkspaceId); // Refresh list
        return res.agent_id;
    },
    updateAgent: async (agentId, updates) => {
        const { currentWorkspaceId } = get();
        if (!currentWorkspaceId) return;

        await updateAgent(currentWorkspaceId, agentId, updates);

        // Refresh agents to reflect potential name changes
        await get().loadAgents(currentWorkspaceId);
    },
    deleteAgent: async (agentId) => {
        const { currentWorkspaceId, loadAgents } = get();
        await import('./lib/api').then(m => m.deleteAgent(agentId)); // call api directly or via import
        if (currentWorkspaceId) await loadAgents(currentWorkspaceId);
    },

    createWorkspace: async (name) => {
        await import('./lib/api').then(m => m.createWorkspace(name));
        await get().loadWorkspaces();
    },
    renameWorkspace: async (id, name) => {
        await import('./lib/api').then(m => m.renameWorkspace(id, name));
        await get().loadWorkspaces();
    },
    deleteWorkspace: async (id) => {
        await import('./lib/api').then(m => m.deleteWorkspace(id));
        await get().loadWorkspaces();
        // If current workspace was deleted, loadWorkspaces logic will handle resetting selection
    },
    applyChange: async (change) => {
        await applyChange(change.file_path, change.original_content, change.new_content, change.diff_lines);

        // Remove from pending list
        set((state) => ({
            pendingChanges: state.pendingChanges.filter(c => c.file_path !== change.file_path)
        }));
    },
    listFiles: async (type) => {
        const { currentWorkspaceId, currentAgentId } = get();
        if (!currentWorkspaceId || !currentAgentId) return [];
        const res = await fetchFiles(currentWorkspaceId, currentAgentId, type);
        return res.files;
    },
    uploadFiles: async (type, files) => {
        const { currentWorkspaceId, currentAgentId } = get();
        if (!currentWorkspaceId || !currentAgentId) return;
        await uploadFiles(currentWorkspaceId, currentAgentId, type, files);
    },
    deleteFile: async (type, filename) => {
        const { currentWorkspaceId, currentAgentId } = get();
        if (!currentWorkspaceId || !currentAgentId) return;
        await deleteFile(currentWorkspaceId, currentAgentId, type, filename);
    },
    processKnowledge: async () => {
        const { currentWorkspaceId, currentAgentId } = get();
        if (!currentWorkspaceId || !currentAgentId) return;
        return await processKnowledgeBase(currentWorkspaceId, currentAgentId);
    },
    // ============================================================
    // Workflow Mode Methods
    // ============================================================
    generateWorkflowPlan: async (userRequest: string) => {
        console.log("[Store] generateWorkflowPlan called, userRequest:", userRequest)
        const { currentWorkspaceId, currentGroupId, workflowMode } = get();
        console.log("[Store] currentWorkspaceId:", currentWorkspaceId, "currentGroupId:", currentGroupId, "workflowMode:", workflowMode)

        // Fallback to legacy mode if not in workflow mode
        if (!workflowMode || !currentGroupId) {
            console.log("[Store] Fallback to sendChatMessage")
            return get().sendChatMessage(userRequest);
        }
        set({ isLoading: true });
        console.log("[Store] isLoading set to true")
        try {
            const { generateWorkflowPlan } = await import('./lib/api');
            console.log("[Store] API module imported")

            // Add user message
            get().addMessage({ role: 'user', content: userRequest });
            console.log("[Store] User message added")

            // Generate workflow plan
            console.log("[Store] Calling API generateWorkflowPlan...")
            const res = await generateWorkflowPlan(
                currentWorkspaceId!,
                currentGroupId,
                userRequest
            );
            console.log("[Store] API returned:", res)

            // Store for user approval
            set({ pendingWorkflow: res.workflow, isLoading: false });
            console.log("[Store] pendingWorkflow set, isLoading = false")
        } catch (error) {
            console.error('[Workflow] Failed to generate plan:', error);
            set({ isLoading: false, pendingWorkflow: null });
        }
    },
    setPendingWorkflow: (workflow: any) => {
        set({ pendingWorkflow: workflow });
    },

    executeWorkflow: async () => {
        const { currentWorkspaceId, currentGroupId, pendingWorkflow, messages } = get();
        if (!pendingWorkflow || !currentGroupId) return;

        set({ isLoading: true, pendingWorkflow: null });
        const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000/api' : '/api');

        try {
            const response = await fetch(`${API_BASE_URL}/group/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    workspace_id: currentWorkspaceId,
                    group_id: currentGroupId,
                    workflow: pendingWorkflow,
                    history: messages
                })
            });

            if (!response.ok) throw new Error(response.statusText);
            if (!response.body) throw new Error("No response body");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            console.log("[Store] Starting SSE stream...");

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log("[Store] Stream complete");
                    break;
                }

                buffer += decoder.decode(value, { stream: true });

                // Process buffer line by line
                const lines = buffer.split('\n\n'); // SSE events are separated by double newline
                buffer = lines.pop() || ''; // Keep the last incomplete chunk

                for (const block of lines) {
                    if (!block.trim()) continue;

                    const eventMatch = block.match(/^event: (.*)$/m);
                    const dataMatch = block.match(/^data: (.*)$/m); // 's' flag for dotAll not needed if single line data

                    if (eventMatch && dataMatch) {
                        const eventType = eventMatch[1].trim();
                        const dataStr = dataMatch[1].trim();

                        try {
                            const data = JSON.parse(dataStr);
                            console.log(`[Store] SSE Event: ${eventType}`, data);

                            if (eventType === 'agent_message') {
                                // Add to store using existing action
                                const newMsg: Message = {
                                    role: 'assistant',
                                    content: data.content,
                                    name: data.name,
                                    shouldAnimate: true
                                };
                                get().addGroupMessage(currentGroupId, newMsg);

                            } else if (eventType === 'finish') {
                                console.log("[Store] Workflow finished event received");
                            } else if (eventType === 'error') {
                                console.error("[Store] Workflow error:", data);
                                const errorMsg: Message = {
                                    role: 'assistant',
                                    name: 'System',
                                    content: `System Error: ${data.content}`
                                };
                                get().addGroupMessage(currentGroupId, errorMsg);
                            }
                        } catch (e) {
                            console.error("[Store] Failed to parse SSE data:", e, "Block:", block);
                        }
                    }
                }
            }

            set({ isLoading: false });
            // Optionally reload perfect history from server to be sure
            // get().loadGroupMessages(currentGroupId); 

        } catch (error) {
            console.error('[Workflow] Failed to execute:', error);
            set({ isLoading: false });
            // Add error message to UI
            const errorMsg: Message = {
                role: 'assistant',
                name: 'System',
                content: `Execution Connection Error: ${error}`
            };
            get().addGroupMessage(currentGroupId, errorMsg);
        }
    },
    cancelWorkflow: () => {
        set({ pendingWorkflow: null });
    },

    startNewSession: async () => {
        const state = get();
        const contextId = state.currentAgentId || state.currentGroupId;
        if (!contextId) return;

        const isGroupMode = !!state.currentGroupId;
        const currentMessages = isGroupMode
            ? (state.groupMessages[contextId] || [])
            : state.messages;

        // Save existing conversation if there are messages
        if (currentMessages.length > 0) {
            const sessionId = state.currentSessionId || sessionManager.generateSessionId();
            sessionManager.saveSession(contextId, sessionId, currentMessages);
        }

        // Clear backend history for group chat
        if (isGroupMode && state.currentWorkspaceId) {
            try {
                const { clearGroupMessages } = await import('./lib/api');
                await clearGroupMessages(state.currentWorkspaceId, contextId);
            } catch (error) {
                console.error("Failed to clear backend group messages:", error);
            }
        }

        // Create fresh session and clear the relevant message store
        const newSessionId = sessionManager.generateSessionId();
        if (isGroupMode) {
            set((s) => ({
                groupMessages: { ...s.groupMessages, [contextId]: [] },
                currentSessionId: newSessionId
            }));
        } else {
            set((s) => ({
                messages: [],
                chatHistory: { ...s.chatHistory, [contextId]: [] },
                currentSessionId: newSessionId
            }));
        }
    },

    switchSession: (sessionId: string) => {
        const state = get();
        const contextId = state.currentAgentId || state.currentGroupId;
        if (!contextId) return;

        const isGroupMode = !!state.currentGroupId;
        const currentMessages = isGroupMode
            ? (state.groupMessages[contextId] || [])
            : state.messages;

        // Save current session before switching
        if (currentMessages.length > 0 && state.currentSessionId) {
            sessionManager.saveSession(contextId, state.currentSessionId, currentMessages);
        }

        const session = sessionManager.loadSession(contextId, sessionId);
        if (!session) return;

        if (isGroupMode) {
            set((s) => ({
                groupMessages: { ...s.groupMessages, [contextId]: session.messages },
                currentSessionId: sessionId
            }));
        } else {
            set((s) => ({
                messages: session.messages,
                chatHistory: { ...s.chatHistory, [contextId]: session.messages },
                currentSessionId: sessionId
            }));
        }
    },

    // Auth Actions
    setAuth: (token, user) => {
        localStorage.setItem('auth_token', token);
        localStorage.setItem('auth_user', JSON.stringify(user));
        set({ token, user, isAuthenticated: true });
    },
    logout: () => {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        set({ token: null, user: null, isAuthenticated: false });
    },
    initAuth: () => {
        const token = localStorage.getItem('auth_token');
        const userStr = localStorage.getItem('auth_user');
        if (token && userStr) {
            try {
                const user = JSON.parse(userStr);
                set({ token, user, isAuthenticated: true });
            } catch {
                set({ token: null, user: null, isAuthenticated: false });
            }
        }
    },
    openLoginModal: () => set({ showLoginModal: true }),
    closeLoginModal: () => set({ showLoginModal: false }),
    requireAuth: (callback) => {
        const { isAuthenticated } = get();
        if (!isAuthenticated) {
            set({ showLoginModal: true });
            return false;
        }
        if (callback) callback();
        return true;
    },
}));
