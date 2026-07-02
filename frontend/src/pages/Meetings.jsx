import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { UploadCloud } from 'lucide-react';

export default function Meetings() {
    const [meetings, setMeetings] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.get('/meetings')
            .then(res => {
                setMeetings(res.data);
                setLoading(false);
            })
            .catch(err => console.error("Error fetching meetings", err));
    }, []);

    if (loading) return <div style={{textAlign: 'center', marginTop: '5rem'}}>Loading...</div>;

    return (
        <div className="animate-fade-in delay-1">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div>
                    <h1>Meetings</h1>
                    <p>All recorded and uploaded meetings.</p>
                </div>
                <Link to="/upload" className="btn btn-primary">
                    <UploadCloud size={18} /> Upload New
                </Link>
            </div>

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
                                <td style={{ fontWeight: 500 }}>
                                    <Link to={`/meetings/${meeting.id}/view`}>{meeting.title}</Link>
                                </td>
                                <td style={{ color: 'var(--text-secondary)' }}>
                                    {new Date(meeting.created_at).toLocaleDateString()}
                                </td>
                                <td>
                                    <span className={`badge badge-${meeting.status}`}>{meeting.status}</span>
                                </td>
                                <td>
                                    <Link to={`/meetings/${meeting.id}/view`} className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem' }}>
                                        View Details
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
