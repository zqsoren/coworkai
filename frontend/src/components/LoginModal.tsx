import React, { useState } from 'react';
import { authLogin, authRegister } from '../lib/api';

interface LoginModalProps {
    onLoginSuccess: (token: string, user: { id: string; username: string; phone: string }) => void;
}

const LoginModal: React.FC<LoginModalProps> = ({ onLoginSuccess }) => {
    const [mode, setMode] = useState<'login' | 'register'>('login');
    const [username, setUsername] = useState('');
    const [phone, setPhone] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            if (mode === 'register') {
                const res = await authRegister(username, phone, password);
                localStorage.setItem('auth_token', res.token);
                localStorage.setItem('auth_user', JSON.stringify(res.user));
                onLoginSuccess(res.token, res.user);
            } else {
                const res = await authLogin(phone, password);
                localStorage.setItem('auth_token', res.token);
                localStorage.setItem('auth_user', JSON.stringify(res.user));
                onLoginSuccess(res.token, res.user);
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || '操作失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 9999,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'linear-gradient(135deg, #0f0f23 0%, #1a1a3e 50%, #0f0f23 100%)',
        }}>
            <div style={{
                width: 380, padding: 36, borderRadius: 16,
                background: 'rgba(30, 30, 60, 0.85)',
                backdropFilter: 'blur(24px)',
                border: '1px solid rgba(255,255,255,0.08)',
                boxShadow: '0 24px 80px rgba(0,0,0,0.5)',
            }}>
                {/* Logo / Title */}
                <div style={{ textAlign: 'center', marginBottom: 28 }}>
                    <div style={{ fontSize: 32, marginBottom: 4 }}>⚡</div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#fff', margin: 0 }}>AgentOS</h1>
                    <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>
                        智能体操作系统
                    </p>
                </div>

                {/* Tab Switcher */}
                <div style={{ display: 'flex', gap: 0, marginBottom: 24, borderRadius: 8, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.1)' }}>
                    {(['login', 'register'] as const).map(tab => (
                        <button
                            key={tab}
                            onClick={() => { setMode(tab); setError(''); }}
                            style={{
                                flex: 1, padding: '10px 0', border: 'none', cursor: 'pointer',
                                fontSize: 14, fontWeight: 500,
                                background: mode === tab ? 'rgba(99, 102, 241, 0.3)' : 'transparent',
                                color: mode === tab ? '#a5b4fc' : 'rgba(255,255,255,0.4)',
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
                            padding: '8px 12px', borderRadius: 8, marginBottom: 16,
                            background: 'rgba(239, 68, 68, 0.15)', color: '#fca5a5',
                            fontSize: 13, border: '1px solid rgba(239, 68, 68, 0.2)'
                        }}>
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            width: '100%', padding: '12px 0', borderRadius: 10,
                            border: 'none', cursor: loading ? 'wait' : 'pointer',
                            fontSize: 15, fontWeight: 600,
                            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                            color: '#fff',
                            opacity: loading ? 0.6 : 1,
                            transition: 'opacity 0.2s',
                        }}
                    >
                        {loading ? '请稍候...' : (mode === 'login' ? '登录' : '注册')}
                    </button>
                </form>
            </div>
        </div>
    );
};

const inputStyle: React.CSSProperties = {
    width: '100%', padding: '11px 14px', borderRadius: 10,
    border: '1px solid rgba(255,255,255,0.1)',
    background: 'rgba(255,255,255,0.05)',
    color: '#fff', fontSize: 14,
    marginBottom: 14, outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.2s',
};

export default LoginModal;
