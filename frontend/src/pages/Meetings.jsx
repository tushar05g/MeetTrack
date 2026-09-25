import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { UploadCloud, Search, Calendar, Clock, Video, ArrowRight, Filter } from 'lucide-react';

export default function Meetings() {
    const [meetings, setMeetings] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterStatus, setFilterStatus] = useState('all');

    useEffect(() => {
        api.get('/meetings')
            .then(res => {
                setMeetings(res.data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching meetings", err);
                setLoading(false);
            });
    }, []);

    const filteredMeetings = meetings.filter(meeting => {
        const matchesSearch = meeting.title.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesStatus = filterStatus === 'all' || meeting.status === filterStatus;
        return matchesSearch && matchesStatus;
    });

    if (loading) {
        return (
            <div style={{ minHeight: '60vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}>
                <div style={{ width: '38px', height: '38px', borderRadius: '50%', border: '3px solid rgba(99, 102, 241, 0.2)', borderTopColor: 'var(--accent-color)', animation: 'spin 0.8s linear infinite' }}></div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: 500 }}>Loading sessions archive...</div>
            </div>
        );
    }

    return (
        <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1.25rem' }}>
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
                        <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.12em', padding: '0.2rem 0.6rem', borderRadius: '999px', background: 'rgba(99, 102, 241, 0.15)', color: '#a5b4fc', border: '1px solid rgba(99, 102, 241, 0.3)', fontWeight: 700 }}>
                            Session Archive
                        </span>
                    </div>
                    <h1 style={{ margin: 0 }}>All Meetings</h1>
                    <p style={{ margin: '0.35rem 0 0', color: 'var(--text-secondary)' }}>
                        Browse, filter, and inspect transcripts and action items from your recorded sessions.
                    </p>
                </div>
                <Link to="/upload" className="btn btn-primary">
                    <UploadCloud size={17} />
                    <span>Upload Recording</span>
                </Link>
            </div>

            {/* Filter & Search Bar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                {/* Search Input */}
                <div style={{ position: 'relative', flex: 1, minWidth: '260px', maxWidth: '420px' }}>
                    <Search size={17} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input 
                        type="text" 
                        placeholder="Search meetings by title..." 
                        value={searchTerm} 
                        onChange={(e) => setSearchTerm(e.target.value)}
                        style={{ paddingLeft: '2.75rem', height: '42px' }}
                    />
                </div>

                {/* Status Filter Pills */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--text-muted)', fontSize: '0.82rem', marginRight: '0.25rem' }}>
                        <Filter size={14} />
                        <span>Filter:</span>
                    </div>
                    {['all', 'done', 'processing', 'pending', 'failed'].map((st) => (
                        <button
                            key={st}
                            onClick={() => setFilterStatus(st)}
                            style={{
                                padding: '0.35rem 0.85rem',
                                borderRadius: '999px',
                                border: filterStatus === st ? '1px solid rgba(99, 102, 241, 0.5)' : '1px solid var(--border-color)',
                                background: filterStatus === st ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                                color: filterStatus === st ? '#c7d2fe' : 'var(--text-secondary)',
                                fontSize: '0.78rem',
                                fontWeight: filterStatus === st ? 700 : 500,
                                cursor: 'pointer',
                                textTransform: 'capitalize',
                                transition: 'var(--transition)'
                            }}
                        >
                            {st}
                        </button>
                    ))}
                </div>
            </div>

            {/* Meetings Table */}
            <div className="table-container">
                <table className="table">
                    <thead>
                        <tr>
                            <th>Meeting Title</th>
                            <th>Recorded Date</th>
                            <th>AI Pipeline Status</th>
                            <th style={{ textAlign: 'right' }}>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredMeetings.length === 0 ? (
                            <tr>
                                <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '4rem 1rem' }}>
                                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
                                        <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: 'rgba(255, 255, 255, 0.04)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                                            <Video size={24} />
                                        </div>
                                        <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '1.05rem' }}>
                                            {searchTerm || filterStatus !== 'all' ? 'No matching meetings found' : 'No meetings in your workspace'}
                                        </div>
                                        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: '360px' }}>
                                            {searchTerm || filterStatus !== 'all' 
                                                ? 'Try adjusting your search query or status filter above.' 
                                                : 'Upload an audio file or dispatch the meeting bot to record and transcribe your first session.'}
                                        </div>
                                        {!searchTerm && filterStatus === 'all' && (
                                            <Link to="/upload" className="btn btn-primary" style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
                                                Upload Recording Now
                                            </Link>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ) : filteredMeetings.map(meeting => {
                            const displayTimeStr = meeting.scheduled_time || meeting.created_at;
                            const formattedDate = new Date(displayTimeStr.replace(' ', 'T') + (displayTimeStr.endsWith('Z') ? '' : 'Z'));
                            return (
                            <tr key={meeting.id}>
                                <td>
                                    <Link 
                                        to={`/meetings/${meeting.id}/view`} 
                                        style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'inline-flex', alignItems: 'center', gap: '0.85rem' }}
                                    >
                                        <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.1))', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#a5b4fc', border: '1px solid rgba(99, 102, 241, 0.25)', flexShrink: 0 }}>
                                            <Video size={18} />
                                        </div>
                                        <span style={{ fontSize: '0.95rem' }}>{meeting.title}</span>
                                    </Link>
                                </td>
                                <td>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', color: 'var(--text-secondary)', fontSize: '0.86rem' }}>
                                            <Calendar size={14} style={{ color: 'var(--text-muted)' }} />
                                            <span>{formattedDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                                        </div>
                                        <div style={{ fontSize: '0.8rem', opacity: 0.8, paddingLeft: '1.35rem', color: 'var(--text-secondary)' }}>
                                            {formattedDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                        </div>
                                    </div>
                                </td>
                                <td>
                                    <span className={`badge badge-${meeting.status}`}>
                                        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'currentColor', display: 'inline-block' }}></span>
                                        <span>{meeting.status}</span>
                                    </span>
                                </td>
                                <td style={{ textAlign: 'right' }}>
                                    <Link 
                                        to={`/meetings/${meeting.id}/view`} 
                                        className="btn btn-secondary" 
                                        style={{ padding: '0.45rem 0.95rem', fontSize: '0.82rem', gap: '0.4rem' }}
                                    >
                                        <span>View Details</span>
                                        <ArrowRight size={13} />
                                    </Link>
                                </td>
                            </tr>
                            );
                            })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
