/**
 * SessionManager - 会话管理工具
 * 优先使用 API 持久化到 Supabase，localStorage 作为离线缓存
 */
import { saveChatSession, listChatSessions, loadChatSession, deleteChatSession } from '../lib/api';
import type { ChatSessionMeta, ChatSession } from '../lib/api';

export interface SessionMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
    name?: string;
    is_plan?: boolean;
}

export interface SessionMeta {
    id: string;
    contextId: string; // agentId or groupId
    title: string; // 第一条用户消息前20字
    preview: string; // 最后一条消息摘要
    createdAt: string; // ISO string
    updatedAt: string; // ISO string
    messageCount: number;
}

export interface Session extends SessionMeta {
    messages: SessionMessage[];
}

const STORAGE_PREFIX = 'agentos_sessions__';

function getStorageKey(contextId: string): string {
    return `${STORAGE_PREFIX}${contextId}`;
}

function generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

function buildTitle(messages: SessionMessage[]): string {
    const firstUser = messages.find(m => m.role === 'user');
    if (!firstUser) return '新对话';
    return firstUser.content.slice(0, 30).trim() + (firstUser.content.length > 30 ? '...' : '');
}

function buildPreview(messages: SessionMessage[]): string {
    const last = [...messages].reverse().find(m => m.role !== 'system');
    if (!last) return '';
    const content = last.content || '';
    return content.slice(0, 50).trim() + (content.length > 50 ? '...' : '');
}

// ── localStorage helpers (fallback) ──

function loadAllSessionsLocal(contextId: string): Session[] {
    try {
        const raw = localStorage.getItem(getStorageKey(contextId));
        if (!raw) return [];
        return JSON.parse(raw) as Session[];
    } catch {
        return [];
    }
}

function saveAllSessionsLocal(contextId: string, sessions: Session[]): void {
    try {
        const trimmed = sessions.slice(-50);
        localStorage.setItem(getStorageKey(contextId), JSON.stringify(trimmed));
    } catch (e) {
        console.warn('[SessionManager] Failed to write to localStorage:', e);
    }
}

// ── Debounce map to avoid flooding the API ──
const saveTimers = new Map<string, ReturnType<typeof setTimeout>>();

export const sessionManager = {
    /**
     * 保存/更新一个会话（debounced API + 同步 localStorage）
     */
    saveSession(contextId: string, sessionId: string, messages: SessionMessage[]): void {
        if (!contextId || messages.length === 0) return;

        const now = new Date().toISOString();
        const sessions = loadAllSessionsLocal(contextId);
        const existing = sessions.findIndex(s => s.id === sessionId);
        const title = buildTitle(messages);
        const preview = buildPreview(messages);

        const sessionData: Session = {
            id: sessionId,
            contextId,
            title,
            preview,
            createdAt: existing >= 0 ? sessions[existing].createdAt : now,
            updatedAt: now,
            messageCount: messages.length,
            messages: messages.filter(m => !m.is_plan),
        };

        if (existing >= 0) {
            sessions[existing] = sessionData;
        } else {
            sessions.push(sessionData);
        }
        saveAllSessionsLocal(contextId, sessions);

        // Debounced API save (2 seconds)
        const timerKey = `${contextId}__${sessionId}`;
        const existingTimer = saveTimers.get(timerKey);
        if (existingTimer) clearTimeout(existingTimer);

        saveTimers.set(timerKey, setTimeout(() => {
            saveTimers.delete(timerKey);
            const cleanMessages = sessionData.messages.map(m => ({
                role: m.role,
                content: m.content,
                ...(m.name ? { name: m.name } : {}),
            }));
            saveChatSession(sessionId, contextId, title, preview, cleanMessages).catch(err => {
                console.warn('[SessionManager] API save failed, localStorage has the data:', err);
            });
        }, 2000));
    },

    /**
     * 获取会话列表（优先 API，fallback localStorage）
     */
    listSessions(contextId: string): SessionMeta[] {
        // 同步返回 localStorage 数据
        const local = loadAllSessionsLocal(contextId);
        return local
            .map(({ messages: _messages, ...meta }) => meta)
            .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
    },

    /**
     * 异步获取会话列表（从 API）
     */
    async listSessionsAsync(contextId: string): Promise<SessionMeta[]> {
        try {
            const apiSessions = await listChatSessions(contextId);
            // Convert API format to local format
            return apiSessions.map((s: ChatSessionMeta) => ({
                id: s.id,
                contextId: s.context_id,
                title: s.title,
                preview: s.preview,
                createdAt: s.created_at,
                updatedAt: s.updated_at,
                messageCount: s.message_count,
            }));
        } catch {
            // Fallback to localStorage
            return this.listSessions(contextId);
        }
    },

    /**
     * 获取单个会话（含消息体）
     */
    loadSession(contextId: string, sessionId: string): Session | null {
        const sessions = loadAllSessionsLocal(contextId);
        return sessions.find(s => s.id === sessionId) || null;
    },

    /**
     * 异步加载会话（从 API，fallback localStorage）
     */
    async loadSessionAsync(contextId: string, sessionId: string): Promise<Session | null> {
        try {
            const apiSession = await loadChatSession(sessionId) as ChatSession | null;
            if (apiSession) {
                return {
                    id: apiSession.id,
                    contextId: apiSession.context_id,
                    title: apiSession.title,
                    preview: apiSession.preview,
                    createdAt: apiSession.created_at,
                    updatedAt: apiSession.updated_at,
                    messageCount: apiSession.message_count,
                    messages: apiSession.messages as SessionMessage[],
                };
            }
        } catch {
            // Fallback
        }
        return this.loadSession(contextId, sessionId);
    },

    /**
     * 删除单个会话
     */
    deleteSession(contextId: string, sessionId: string): void {
        const sessions = loadAllSessionsLocal(contextId).filter(s => s.id !== sessionId);
        saveAllSessionsLocal(contextId, sessions);
        // Also delete from API
        deleteChatSession(sessionId).catch(err => {
            console.warn('[SessionManager] API delete failed:', err);
        });
    },

    /**
     * 生成唯一会话 ID
     */
    generateSessionId,

    /**
     * 格式化时间显示
     */
    formatTime(isoString: string): string {
        const date = new Date(isoString);
        const now = new Date();
        const diff = now.getTime() - date.getTime();

        if (diff < 60000) return '刚刚';
        if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
        if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`;

        return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
    }
};
