import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { Video, AlertCircle, Mic } from 'lucide-react';

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
            .catch(err => console.error("Error fetching tasks", err));
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
                alert(res.data.message);
                setVoiceFile(null);
                setEmail('');
            })
            .catch(err => {
                console.error(err);
                alert("Voice profile upload failed.");
            })
            .finally(() => setUploadingVoice(false));
    };

    if (loading) return <div style={{textAlign: 'center', marginTop: '5rem'}}>Loading...</div>;

    return (
        <div className="animate-fade-in delay-1">
            <h1>Dashboard</h1>
            <p>Welcome back to MeetTrack. Here's what's happening today.</p>

            <div className="grid-cards" style={{ marginBottom: '2.5rem' }}>
                <div className="glass-panel stat-card">
                    <div className="stat-icon blue">
                        <Video />
                    </div>
                    <div className="stat-content">
                        <h4>Total Meetings</h4>
                        <div className="value">{totalMeetings}</div>
                    </div>
                </div>
                
                <div className="glass-panel stat-card">
                    <div className="stat-icon warning">
                        <AlertCircle />
                    </div>
                    <div className="stat-content">
                        <h4>Open Tasks</h4>
                        <div className="value">{openTasks}</div>
                    </div>
                </div>
            </div>
            
            <h2>Voice Biometrics Registration</h2>
            <div className="glass-panel" style={{ marginBottom: '2.5rem', padding: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                    <div className="stat-icon" style={{ background: 'rgba(255, 255, 255, 0.1)', color: 'var(--text-primary)' }}>
                        <Mic />
                    </div>
                    <div>
                        <h4 style={{ margin: 0 }}>Register Your Voice</h4>
                        <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Upload a 30-second audio clip of your voice to be automatically identified in future meetings.</p>
                    </div>
                </div>
                <form onSubmit={handleVoiceUpload} style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                    <div className="form-group" style={{ flex: 1, minWidth: '200px', margin: 0 }}>
                        <label>Your Email</label>
                        <input type="email" className="input" placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)} required />
                    </div>
                    <div className="form-group" style={{ flex: 1, minWidth: '250px', margin: 0 }}>
                        <label>Voice Sample (WAV/MP3)</label>
                        <input type="file" className="input" accept="audio/*" onChange={e => setVoiceFile(e.target.files[0])} required />
                    </div>
                    <button type="submit" className="btn btn-primary" disabled={uploadingVoice} style={{ height: '42px' }}>
                        {uploadingVoice ? 'Uploading...' : 'Register Voice'}
                    </button>
                </form>
            </div>

            <h2>Recent Meetings</h2>
            <div className="glass-panel table-container">
                <table className="table">
                    <thead>
                        <tr>
                            <th>Title</th>
                            <th>Date</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {meetings.length === 0 ? (
                            <tr>
                                <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                                    No meetings found. <Link to="/upload">Upload one now.</Link>
                                </td>
                            </tr>
                        ) : meetings.map(meeting => (
                            <tr key={meeting.id}>
                                <td style={{ fontWeight: 500 }}>{meeting.title}</td>
                                <td style={{ color: 'var(--text-secondary)' }}>
                                    {new Date(meeting.created_at).toLocaleDateString()}
                                </td>
                                <td>
                                    <span className={`badge badge-${meeting.status}`}>{meeting.status}</span>
                                </td>
                                <td>
                                    <Link to={`/meetings/${meeting.id}/view`} className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem' }}>
                                        View
                                    </Link>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
