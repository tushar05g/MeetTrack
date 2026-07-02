import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api';
import { ArrowLeft, User, Calendar, Check, AlertCircle, RefreshCw, CheckCircle2 } from 'lucide-react';

export default function MeetingDetail() {
    const { id } = useParams();
    const [meeting, setMeeting] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchMeeting();
    }, [id]);

    const fetchMeeting = async () => {
        try {
            const res = await api.get(`/meetings/${id}`);
            setMeeting(res.data);
            setLoading(false);
        } catch (err) {
            console.error(err);
            setLoading(false);
        }
    };

    const markTaskDone = async (taskId) => {
        try {
            await api.patch(`/tasks/${taskId}`, { status: 'done' });
            // Update local state
            setMeeting(prev => ({
                ...prev,
                tasks: prev.tasks.map(t => t.id === taskId ? { ...t, status: 'done' } : t)
            }));
        } catch (err) {
            alert('Error updating task: ' + err.message);
        }
    };

    if (loading) return <div style={{textAlign: 'center', marginTop: '5rem'}}>Loading...</div>;
    if (!meeting) return <div style={{textAlign: 'center', marginTop: '5rem'}}>Meeting not found.</div>;

    return (
        <div className="animate-fade-in delay-1">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <Link to="/meetings" style={{ fontSize: '0.9rem', marginBottom: '0.5rem', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
                        <ArrowLeft size={16} /> Back to Meetings
                    </Link>
                    <h1>{meeting.title}</h1>
                    <p style={{ marginBottom: 0 }}>Uploaded on {new Date(meeting.created_at).toLocaleDateString()}</p>
                </div>
                <span className={`badge badge-${meeting.status}`}>{meeting.status}</span>
            </div>

            {meeting.status === 'done' ? (
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr', gap: '2rem' }}>
                    
                    {/* Transcript Column */}
                    <div className="glass-panel">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                            <h3>Transcript</h3>
                        </div>
                        
                        <div className="transcript-box">
                            {meeting.transcript && meeting.transcript.segments && meeting.transcript.segments.length > 0 ? (
                                meeting.transcript.segments.map((segment, idx) => (
                                    <div className="segment" key={idx}>
                                        <div className="segment-header">
                                            <span className="speaker-badge">{segment.speaker}</span>
                                            <span className="timestamp">{segment.start.toFixed(2)}s - {segment.end.toFixed(2)}s</span>
                                        </div>
                                        <div className="segment-text">
                                            {segment.text}
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <p>No transcript data available.</p>
                            )}
                        </div>
                    </div>

                    {/* Tasks Column */}
                    <div className="glass-panel">
                        <h3>Action Items</h3>
                        <p style={{ fontSize: '0.9rem', marginBottom: '1.5rem' }}>Automatically extracted from the meeting.</p>
                        
                        <div className="tasks-list">
                            {meeting.tasks && meeting.tasks.length > 0 ? (
                                meeting.tasks.map(task => (
                                    <div className="task-item" key={task.id}>
                                        <div className="task-header">
                                            <div className="task-desc">{task.description}</div>
                                        </div>
                                        <div className="task-meta" style={{ marginBottom: '1rem' }}>
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                                <User size={14} /> {task.owner || 'Unassigned'}
                                            </span>
                                            {task.deadline && (
                                                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--warning-color)' }}>
                                                    <Calendar size={14} /> {task.deadline}
                                                </span>
                                            )}
                                        </div>
                                        
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <span className={`badge badge-${task.status}`}>
                                                {task.status}
                                            </span>
                                            
                                            {task.status !== 'done' && (
                                                <button 
                                                    className="btn btn-secondary" 
                                                    style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }} 
                                                    onClick={() => markTaskDone(task.id)}
                                                >
                                                    <Check size={14} /> Mark Done
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div style={{ textAlign: 'center', padding: '2rem 0', color: 'var(--text-secondary)' }}>
                                    <CheckCircle2 size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                                    <p>No action items were extracted.</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            ) : meeting.status === 'failed' ? (
                <div className="glass-panel" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
                    <AlertCircle size={64} color="var(--danger-color)" style={{ marginBottom: '1rem' }} />
                    <h2>Processing Failed</h2>
                    <p>There was an error processing this meeting. Please try uploading it again.</p>
                </div>
            ) : (
                <div className="glass-panel" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
                    <RefreshCw size={48} className="spin" color="var(--accent-color)" style={{ marginBottom: '1rem' }} />
                    <h2>Processing...</h2>
                    <p>This meeting is currently being processed. Check back later.</p>
                </div>
            )}
        </div>
    );
}
