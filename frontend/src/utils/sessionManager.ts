/**
 * SessionManager - 会话管理工具
 * 使用 localStorage 持久化存储对话会话
 */

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

function loadAllSessions(contextId: string): Session[] {
    try {
        const raw = localStorage.getItem(getStorageKey(contextId));
        if (!raw) return [];
        return JSON.parse(raw) as Session[];
    } catch {
        return [];
    }
}

function saveAllSessions(contextId: string, sessions: Session[]): void {
    try {
        // Keep at most 50 sessions per context
        const trimmed = sessions.slice(-50);
        localStorage.setItem(getStorageKey(contextId), JSON.stringify(trimmed));
    } catch (e) {
        console.warn('[SessionManager] Failed to write to localStorage:', e);
    }
}

export const sessionManager = {
    /**
     * 保存/更新一个会话
     */
    saveSession(contextId: string, sessionId: string, messages: SessionMessage[]): void {
        if (!contextId || messages.length === 0) return;

        const sessions = loadAllSessions(contextId);
        const now = new Date().toISOString();
        const existing = sessions.findIndex(s => s.id === sessionId);

        const sessionData: Session = {
            id: sessionId,
            contextId,
            title: buildTitle(messages),
            preview: buildPreview(messages),
            createdAt: existing >= 0 ? sessions[existing].createdAt : now,
            updatedAt: now,
            messageCount: messages.length,
            messages: messages.filter(m => !m.is_plan), // Don't save plan messages
        };

        if (existing >= 0) {
            sessions[existing] = sessionData;
        } else {
            sessions.push(sessionData);
        }

        saveAllSessions(contextId, sessions);
    },

    /**
     * 获取会话列表（元数据，不含消息体）
     */
    listSessions(contextId: string): SessionMeta[] {
        const sessions = loadAllSessions(contextId);
        return sessions
            .map(({ messages: _messages, ...meta }) => meta)
            .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
    },

    /**
     * 获取单个会话（含消息体）
     */
    loadSession(contextId: string, sessionId: string): Session | null {
        const sessions = loadAllSessions(contextId);
        return sessions.find(s => s.id === sessionId) || null;
    },

    /**
     * 删除单个会话
     */
    deleteSession(contextId: string, sessionId: string): void {
        const sessions = loadAllSessions(contextId).filter(s => s.id !== sessionId);
        saveAllSessions(contextId, sessions);
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
