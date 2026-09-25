import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { Video, CheckSquare, Mic, ArrowRight, UploadCloud, Clock, ShieldCheck } from 'lucide-react';

export default function Dashboard() {
    const [meetings, setMeetings] = useState([]);
    const [openTasks, setOpenTasks] = useState(0);
    const [totalMeetings, setTotalMeetings] = useState(0);
    const [loading, setLoading] = useState(true);
    const [email, setEmail] = useState('');
    const [voiceFile, setVoiceFile] = useState(null);
    const [uploadingVoice, setUploadingVoice] = useState(false);

    useEffect(() => {
        // Fetch all meetings to derive stats
        api.get('/meetings')
            .then(res => {
                setMeetings(res.data.slice(0, 5)); // recent 5
                setTotalMeetings(res.data.length);
            })
            .catch(err => console.error("Error fetching meetings", err));

        api.get('/tasks')
            .then(res => {
                const open = res.data.filter(t => t.status !== 'done').length;
                setOpenTasks(open);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching tasks", err);
                setLoading(false);
            });
    }, []);

    const handleVoiceUpload = (e) => {
        e.preventDefault();
        if (!voiceFile || !email) {
            alert("Please provide an email and select an audio file.");
            return;
        }
        setUploadingVoice(true);
        const formData = new FormData();
        formData.append('email', email);
        formData.append('file', voiceFile);
        
        api.post('/users/voice_profile', formData)
            .then(res => {
                alert(res.data.message || "Voice profile registered successfully!");
                setVoiceFile(null);
                setEmail('');
            })
            .catch(err => {
                console.error(err);
                alert("Voice profile upload failed.");
            })
            .finally(() => setUploadingVoice(false));
    };

    if (loading) {
        return (
            <div style={{ minHeight: '60vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}>
                <div style={{ width: '38px', height: '38px', borderRadius: '50%', border: '3px solid rgba(99, 102, 241, 0.2)', borderTopColor: 'var(--accent-color)', animation: 'spin 0.8s linear infinite' }}></div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: 500 }}>Loading workspace intelligence...</div>
            </div>
        );
    }

    return (
        <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '2.25rem' }}>
            {/* Hero Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1.25rem' }}>
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.5rem' }}>
                        <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.12em', padding: '0.2rem 0.6rem', borderRadius: '999px', background: 'rgba(99, 102, 241, 0.15)', color: '#a5b4fc', border: '1px solid rgba(99, 102, 241, 0.3)', fontWeight: 700 }}>
                            Workspace Overview
                        </span>
                    </div>
                    <h1 style={{ margin: 0 }}>Meeting Intelligence</h1>
                    <p style={{ margin: '0.35rem 0 0', maxWidth: '600px', color: 'var(--text-secondary)' }}>
                        Automated live bot recording, speaker diarization, and actionable task extraction across your sessions.
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                    <Link to="/upload" className="btn btn-primary">
                        <UploadCloud size={17} />
                        <span>Upload Audio</span>
                    </Link>
                    <Link to="/meetings" className="btn btn-secondary">
                        <Mic size={17} />
                        <span>All Meetings</span>
                    </Link>
                </div>
            </div>

            {/* Metric Stat Cards */}
            <div className="grid-cards">
                <div className="glass-panel stat-card">
                    <div className="stat-icon blue">
                        <Video size={24} />
                    </div>
                    <div className="stat-content">
                        <h4>Total Sessions</h4>
                        <div className="value">{totalMeetings}</div>
                    </div>
                </div>
                
                <div className="glass-panel stat-card">
                    <div className="stat-icon warning">
                        <CheckSquare size={24} />
                    </div>
                    <div className="stat-content">
                        <h4>Pending Tasks</h4>
                        <div className="value">{openTasks}</div>
                    </div>
                </div>

                <div className="glass-panel stat-card">
                    <div className="stat-icon green">
                        <ShieldCheck size={24} />
                    </div>
                    <div className="stat-content">
                        <h4>Speaker Biometrics</h4>
                        <div className="value" style={{ fontSize: '1.25rem', marginTop: '0.3rem' }}>Ready</div>
                    </div>
                </div>
            </div>
            
            {/* Voice Biometrics Registration Studio Card */}
            <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                    <h2 style={{ margin: 0 }}>Voice Biometrics Enrollment</h2>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Auto-identify who is speaking</span>
                </div>

                <div className="glass-panel" style={{ padding: '1.85rem' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1.25rem', marginBottom: '1.5rem' }}>
                        <div className="stat-icon" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
                            <Mic size={22} />
                        </div>
                        <div>
                            <h4 style={{ margin: '0 0 0.25rem', fontSize: '1.05rem', fontWeight: 700 }}>Enroll Voice Profile</h4>
                            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: 1.5 }}>
                                Upload a 15–30 second clean sample of your voice. Our AI speaker diarization engine will automatically tag your name in future live Google Meet transcripts.
                            </p>
                        </div>
                    </div>

                    <form onSubmit={handleVoiceUpload} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr)) auto', gap: '1rem', alignItems: 'flex-end' }}>
                        <div className="form-group" style={{ margin: 0 }}>
                            <label>Participant Email</label>
                            <input 
                                type="email" 
                                className="input" 
                                placeholder="name@company.com" 
                                value={email} 
                                onChange={e => setEmail(e.target.value)} 
                                required 
                            />
                        </div>
                        <div className="form-group" style={{ margin: 0 }}>
                            <label>Audio Clip (.wav / .mp3)</label>
                            <input 
                                type="file" 
                                className="input" 
                                accept="audio/*" 
                                onChange={e => setVoiceFile(e.target.files[0])} 
                                required 
                            />
                        </div>
                        <button 
                            type="submit" 
                            className="btn btn-primary" 
                            disabled={uploadingVoice} 
                            style={{ height: '44px', minWidth: '160px' }}
                        >
                            {uploadingVoice ? (
                                <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <span style={{ width: '14px', height: '14px', borderRadius: '50%', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', animation: 'spin 0.6s linear infinite' }}></span>
                                    <span>Processing...</span>
                                </span>
                            ) : (
                                <span>Register Profile</span>
                            )}
                        </button>
                    </form>
                </div>
            </div>

            {/* Recent Meetings Table */}
            <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                    <h2 style={{ margin: 0 }}>Recent Meetings</h2>
                    <Link to="/meetings" style={{ fontSize: '0.85rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                        <span>View all sessions</span>
                        <ArrowRight size={14} />
                    </Link>
                </div>

                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>Meeting Session</th>
                                <th>Recorded Date</th>
                                <th>AI Status</th>
                                <th style={{ textAlign: 'right' }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {meetings.length === 0 ? (
                                <tr>
                                    <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '3.5rem 1rem' }}>
                                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
                                            <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: 'rgba(255, 255, 255, 0.04)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                                                <Clock size={22} />
                                            </div>
                                            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>No sessions recorded yet</div>
                                            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: '360px' }}>
                                                Upload an audio file or dispatch the meeting bot to record and transcribe your first session.
                                            </div>
                                            <Link to="/upload" className="btn btn-primary" style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
                                                Upload Recording Now
                                            </Link>
                                        </div>
                                    </td>
                                </tr>
                            ) : meetings.map(meeting => {
                                const displayTimeStr = meeting.scheduled_time || meeting.created_at;
                                const formattedDate = new Date(displayTimeStr.replace(' ', 'T') + (displayTimeStr.endsWith('Z') ? '' : 'Z'));
                                return (
                                <tr key={meeting.id}>
                                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(99, 102, 241, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#a5b4fc' }}>
                                                <Video size={16} />
                                            </div>
                                            <span>{meeting.title}</span>
                                        </div>
                                    </td>
                                    <td style={{ color: 'var(--text-secondary)' }}>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.86rem' }}>
                                                <Clock size={13} style={{ color: 'var(--text-muted)' }} />
                                                <span>{formattedDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                                            </div>
                                            <div style={{ fontSize: '0.8rem', opacity: 0.8, paddingLeft: '1.2rem' }}>
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
                                            style={{ padding: '0.4rem 0.85rem', fontSize: '0.82rem' }}
                                        >
                                            Open Studio
                                        </Link>
                                    </td>
                                </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
