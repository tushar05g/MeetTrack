import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { Video, AlertCircle } from 'lucide-react';

export default function Dashboard() {
    const [meetings, setMeetings] = useState([]);
    const [openTasks, setOpenTasks] = useState(0);
    const [totalMeetings, setTotalMeetings] = useState(0);
    const [loading, setLoading] = useState(true);

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
