import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutGrid, UploadCloud, Mic, CheckSquare, Activity } from 'lucide-react';

export default function Sidebar() {
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

            <div style={{ marginTop: 'auto', paddingTop: '2rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                <p>Status: <span style={{ color: 'var(--success-color)' }}>● Online</span></p>
                <p>NVIDIA GTX 1050 Ti Mode</p>
            </div>
        </nav>
    );
}
