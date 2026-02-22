import React, { useState } from 'react';
import { authLogin, authRegister } from '../lib/api';
import { useStore } from '../store';

const LoginModal: React.FC = () => {
    const { showLoginModal, closeLoginModal, setAuth } = useStore();
    const [mode, setMode] = useState<'login' | 'register'>('login');
    const [username, setUsername] = useState('');
    const [phone, setPhone] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    if (!showLoginModal) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            if (mode === 'register') {
                const res = await authRegister(username, phone, password);
                localStorage.setItem('auth_token', res.token);
                localStorage.setItem('auth_user', JSON.stringify(res.user));
                setAuth(res.token, res.user);
            } else {
                const res = await authLogin(phone, password);
                localStorage.setItem('auth_token', res.token);
                localStorage.setItem('auth_user', JSON.stringify(res.user));
                setAuth(res.token, res.user);
            }
            closeLoginModal();
        } catch (err: any) {
            setError(err.response?.data?.detail || '操作失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div
            style={{
                position: 'fixed', inset: 0, zIndex: 9999,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'rgba(0, 0, 0, 0.3)',
                backdropFilter: 'blur(4px)',
            }}
            onClick={(e) => { if (e.target === e.currentTarget) closeLoginModal(); }}
        >
            <div style={{
                width: 400, padding: 40, borderRadius: 20,
                background: '#ffffff',
                boxShadow: '0 24px 80px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.04)',
                animation: 'fadeInUp 0.25s ease-out',
            }}>
                {/* Logo / Title */}
                <div style={{ textAlign: 'center', marginBottom: 28 }}>
                    <div style={{ fontSize: 36, marginBottom: 6 }}>⚡</div>
                    <h1 style={{ fontSize: 24, fontWeight: 700, color: '#111827', margin: 0, letterSpacing: '-0.5px' }}>
                        基石协作
                    </h1>
                    <p style={{ fontSize: 13, color: '#9ca3af', marginTop: 6 }}>
                        登录后即可使用全部功能
                    </p>
                </div>

                {/* Tab Switcher */}
                <div style={{
                    display: 'flex', gap: 0, marginBottom: 24, borderRadius: 10,
                    overflow: 'hidden', background: '#f3f4f6',
                    padding: 3,
                }}>
                    {(['login', 'register'] as const).map(tab => (
                        <button
                            key={tab}
                            onClick={() => { setMode(tab); setError(''); }}
                            style={{
                                flex: 1, padding: '9px 0', border: 'none', cursor: 'pointer',
                                fontSize: 14, fontWeight: 500, borderRadius: 8,
                                background: mode === tab ? '#ffffff' : 'transparent',
                                color: mode === tab ? '#111827' : '#9ca3af',
                                boxShadow: mode === tab ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                                transition: 'all 0.2s',
                            }}
                        >
                            {tab === 'login' ? '登录' : '注册'}
                        </button>
                    ))}
                </div>

                <form onSubmit={handleSubmit}>
                    {mode === 'register' && (
                        <input
                            type="text"
                            placeholder="用户名"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            required
                            style={inputStyle}
                        />
                    )}
                    <input
                        type="tel"
                        placeholder="手机号"
                        value={phone}
                        onChange={e => setPhone(e.target.value)}
                        required
                        style={inputStyle}
                    />
                    <input
                        type="password"
                        placeholder="密码"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        required
                        style={inputStyle}
                    />

                    {error && (
                        <div style={{
                            padding: '10px 14px', borderRadius: 10, marginBottom: 16,
                            background: '#fef2f2', color: '#dc2626',
                            fontSize: 13, border: '1px solid #fecaca',
                        }}>
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            width: '100%', padding: '12px 0', borderRadius: 12,
                            border: 'none', cursor: loading ? 'wait' : 'pointer',
                            fontSize: 15, fontWeight: 600,
                            background: '#111827',
                            color: '#fff',
                            opacity: loading ? 0.6 : 1,
                            transition: 'all 0.2s',
                        }}
                    >
                        {loading ? '请稍候...' : (mode === 'login' ? '登录' : '注册')}
                    </button>
                </form>
            </div>

            <style>{`
                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(16px) scale(0.97); }
                    to { opacity: 1; transform: translateY(0) scale(1); }
                }
            `}</style>
        </div>
    );
};

const inputStyle: React.CSSProperties = {
    width: '100%', padding: '12px 16px', borderRadius: 12,
    border: '1px solid #e5e7eb',
    background: '#f9fafb',
    color: '#111827', fontSize: 14,
    marginBottom: 14, outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.2s',
};

export default LoginModal;
