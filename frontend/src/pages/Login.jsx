import React, { useState, useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { Mail, Lock, LogIn, AlertCircle, Sparkles, RefreshCw } from 'lucide-react';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    
    const { login } = useContext(AuthContext);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);
        
        try {
            await login(email, password);
            navigate('/dashboard');
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to login. Please check your credentials.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div style={{ 
            minHeight: '100vh', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            padding: '2rem 1rem',
            position: 'relative'
        }}>
            {/* Ambient background glow */}
            <div style={{
                position: 'absolute',
                width: '380px',
                height: '380px',
                borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(99, 102, 241, 0.15), transparent 70%)',
                filter: 'blur(40px)',
                pointerEvents: 'none',
                zIndex: 0
            }} />

            <div className="glass-panel animate-fade-in" style={{ 
                maxWidth: '440px', 
                width: '100%', 
                padding: '2.5rem', 
                borderRadius: '20px', 
                border: '1px solid var(--border-color)',
                boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4)',
                position: 'relative',
                zIndex: 1
            }}>
                {/* Brand Header */}
                <div style={{ textAlign: 'center', marginBottom: '2.25rem' }}>
                    <div style={{
                        width: '52px',
                        height: '52px',
                        borderRadius: '14px',
                        background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
                        color: '#ffffff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        margin: '0 auto 1.25rem',
                        boxShadow: '0 8px 20px rgba(99, 102, 241, 0.4)'
                    }}>
                        <Sparkles size={24} />
                    </div>
                    <h2 style={{ margin: '0 0 0.4rem 0', fontSize: '1.85rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
                        Welcome Back
                    </h2>
                    <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.92rem' }}>
                        Sign in to your MeetTrack workspace
                    </p>
                </div>
                
                {error && (
                    <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '0.6rem', 
                        background: 'rgba(239, 68, 68, 0.1)', 
                        border: '1px solid rgba(239, 68, 68, 0.25)',
                        color: 'var(--danger-color)', 
                        padding: '0.85rem 1rem', 
                        borderRadius: '10px', 
                        marginBottom: '1.5rem', 
                        fontSize: '0.86rem' 
                    }}>
                        <AlertCircle size={16} style={{ flexShrink: 0 }} />
                        <span>{error}</span>
                    </div>
                )}
                
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                            Email Address
                        </label>
                        <div style={{ position: 'relative' }}>
                            <Mail size={17} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                            <input 
                                type="email" 
                                value={email} 
                                onChange={(e) => setEmail(e.target.value)} 
                                style={{ 
                                    width: '100%', 
                                    padding: '0.8rem 1rem 0.8rem 2.75rem', 
                                    borderRadius: '10px', 
                                    border: '1px solid var(--border-color)', 
                                    background: 'var(--bg-secondary)', 
                                    color: 'var(--text-primary)', 
                                    fontSize: '0.92rem',
                                    outline: 'none', 
                                    boxSizing: 'border-box' 
                                }}
                                placeholder="name@company.com"
                                required 
                            />
                        </div>
                    </div>
                    
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                                Password
                            </label>
                        </div>
                        <div style={{ position: 'relative' }}>
                            <Lock size={17} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                            <input 
                                type="password" 
                                value={password} 
                                onChange={(e) => setPassword(e.target.value)} 
                                style={{ 
                                    width: '100%', 
                                    padding: '0.8rem 1rem 0.8rem 2.75rem', 
                                    borderRadius: '10px', 
                                    border: '1px solid var(--border-color)', 
                                    background: 'var(--bg-secondary)', 
                                    color: 'var(--text-primary)', 
                                    fontSize: '0.92rem',
                                    outline: 'none', 
                                    boxSizing: 'border-box' 
                                }}
                                placeholder="••••••••••••"
                                required 
                            />
                        </div>
                    </div>
                    
                    <button 
                        type="submit" 
                        className="btn btn-primary" 
                        style={{ 
                            width: '100%', 
                            marginTop: '0.5rem', 
                            padding: '0.85rem',
                            fontSize: '0.95rem',
                            fontWeight: 600,
                            justifyContent: 'center',
                            gap: '0.5rem'
                        }} 
                        disabled={isLoading}
                    >
                        {isLoading ? (
                            <>
                                <RefreshCw size={16} className="spin" /> Signing in...
                            </>
                        ) : (
                            <>
                                <LogIn size={17} /> Sign In
                            </>
                        )}
                    </button>
                </form>
                
                <div style={{ textAlign: 'center', marginTop: '1.75rem', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                    Don't have an account?{' '}
                    <Link to="/signup" style={{ color: 'var(--accent-hover)', fontWeight: 600 }}>
                        Create an account
                    </Link>
                </div>
            </div>
        </div>
    );
}
