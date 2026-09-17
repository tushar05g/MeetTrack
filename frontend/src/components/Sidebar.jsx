import React, { useContext } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutGrid, UploadCloud, Mic, CheckSquare, Activity, LogOut, User } from 'lucide-react';
import { AuthContext } from '../context/AuthContext';

export default function Sidebar() {
    const { user, logout } = useContext(AuthContext);

    return (
        <nav className="sidebar glass-panel">
            <div className="logo">
                <div className="logo-icon">
                    <Activity size={20} />
                </div>
                MeetTrack
            </div>
            
            <ul className="nav-links">
                <li>
                    <NavLink to="/" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
                        <LayoutGrid size={18} /> Dashboard
                    </NavLink>
                </li>
                <li>
                    <NavLink to="/upload" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
                        <UploadCloud size={18} /> Upload
                    </NavLink>
                </li>
                <li>
                    <NavLink to="/meetings" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
                        <Mic size={18} /> Meetings
                    </NavLink>
                </li>
                <li>
                    <NavLink to="/tasks" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
                        <CheckSquare size={18} /> Tasks
                    </NavLink>
                </li>
            </ul>

            <div style={{ marginTop: 'auto', paddingTop: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {user && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem', background: 'var(--bg-secondary)', borderRadius: '12px' }}>
                        <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--accent-color)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
                            <User size={16} />
                        </div>
                        <div style={{ overflow: 'hidden' }}>
                            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{user.name}</div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{user.email}</div>
                        </div>
                    </div>
                )}
                
                <button 
                    onClick={logout} 
                    className="nav-item" 
                    style={{ background: 'transparent', border: 'none', width: '100%', textAlign: 'left', cursor: 'pointer', color: '#ef4444' }}
                >
                    <LogOut size={18} /> Logout
                </button>

                <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '0.5rem' }}>
                    <p>Status: <span style={{ color: 'var(--success-color)' }}>● Online</span></p>
                    <p>NVIDIA GTX 1050 Ti</p>
                </div>
            </div>
        </nav>
    );
}
