import React, { useContext } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutGrid, UploadCloud, Mic, CheckSquare, Sparkles, LogOut, User } from 'lucide-react';
import { AuthContext } from '../context/AuthContext';

export default function Sidebar() {
    const { user, logout } = useContext(AuthContext);

    return (
        <nav className="sidebar">
            <div className="logo">
                <div className="logo-icon">
                    <Sparkles size={20} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.03em' }}>MeetTrack</span>
                    <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--accent-hover)', fontWeight: 700 }}>AI Intelligence</span>
                </div>
            </div>
            
            <ul className="nav-links">
                <li>
                    <NavLink to="/" end className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
                        <LayoutGrid size={18} />
                        <span>Dashboard</span>
                    </NavLink>
                </li>
                <li>
                    <NavLink to="/upload" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
                        <UploadCloud size={18} />
                        <span>Upload Audio</span>
                    </NavLink>
                </li>
                <li>
                    <NavLink to="/meetings" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
                        <Mic size={18} />
                        <span>Meetings</span>
                    </NavLink>
                </li>
                <li>
                    <NavLink to="/tasks" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
                        <CheckSquare size={18} />
                        <span>Action Items</span>
                    </NavLink>
                </li>
            </ul>

            <div style={{ marginTop: 'auto', paddingTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                {user && (
                    <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '0.75rem', 
                        padding: '0.75rem 0.85rem', 
                        background: 'rgba(255, 255, 255, 0.03)', 
                        border: '1px solid var(--border-color)', 
                        borderRadius: '12px' 
                    }}>
                        <div style={{ 
                            width: '34px', 
                            height: '34px', 
                            borderRadius: '10px', 
                            background: 'var(--accent-gradient)', 
                            display: 'flex', 
                            alignItems: 'center', 
                            justifyContent: 'center', 
                            color: '#fff',
                            fontWeight: 700,
                            fontSize: '0.9rem',
                            flexShrink: 0
                        }}>
                            {user.name ? user.name.charAt(0).toUpperCase() : <User size={16} />}
                        </div>
                        <div style={{ overflow: 'hidden', flex: 1 }}>
                            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                                {user.name}
                            </div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                                {user.email}
                            </div>
                        </div>
                    </div>
                )}
                
                <button 
                    onClick={logout} 
                    className="nav-item" 
                    style={{ 
                        background: 'transparent', 
                        border: '1px solid transparent', 
                        width: '100%', 
                        cursor: 'pointer', 
                        color: '#f87171',
                        padding: '0.65rem 0.85rem'
                    }}
                >
                    <LogOut size={17} />
                    <span>Log Out</span>
                </button>

                <div style={{ 
                    padding: '0.65rem 0.85rem', 
                    borderRadius: '10px', 
                    background: 'rgba(16, 185, 129, 0.06)', 
                    border: '1px solid rgba(16, 185, 129, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    fontSize: '0.74rem',
                    color: 'var(--text-secondary)'
                }}>
                    <span style={{ 
                        width: '7px', 
                        height: '7px', 
                        borderRadius: '50%', 
                        background: 'var(--success-color)', 
                        boxShadow: '0 0 8px var(--success-color)',
                        display: 'inline-block' 
                    }}></span>
                    <span style={{ color: '#6ee7b7', fontWeight: 600 }}>AI Engine Active</span>
                </div>
            </div>
        </nav>
    );
}
