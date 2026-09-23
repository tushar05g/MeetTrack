import React, { useState, useEffect, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api';
import { 
    ArrowLeft, 
    User, 
    Calendar, 
    Check, 
    AlertCircle, 
    RefreshCw, 
    CheckCircle2, 
    Clock, 
    Search, 
    Copy, 
    Sparkles, 
    ListTodo, 
    MessageSquareQuote,
    Filter
} from 'lucide-react';

export default function MeetingDetail() {
    const { id } = useParams();
    const [meeting, setMeeting] = useState(null);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedSpeaker, setSelectedSpeaker] = useState('all');
    const [copied, setCopied] = useState(false);

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

    const formatTimestamp = (seconds) => {
        if (typeof seconds !== 'number' || isNaN(seconds)) return '00:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    // Color palette generator for different speakers
    const speakerColors = useMemo(() => {
        const colors = [
            { bg: 'rgba(99, 102, 241, 0.15)', border: 'rgba(99, 102, 241, 0.35)', text: '#a5b4fc' },
            { bg: 'rgba(16, 185, 129, 0.15)', border: 'rgba(16, 185, 129, 0.35)', text: '#6ee7b7' },
            { bg: 'rgba(245, 158, 11, 0.15)', border: 'rgba(245, 158, 11, 0.35)', text: '#fcd34d' },
            { bg: 'rgba(236, 72, 153, 0.15)', border: 'rgba(236, 72, 153, 0.35)', text: '#f472b6' },
            { bg: 'rgba(14, 165, 233, 0.15)', border: 'rgba(14, 165, 233, 0.35)', text: '#7dd3fc' },
            { bg: 'rgba(168, 85, 247, 0.15)', border: 'rgba(168, 85, 247, 0.35)', text: '#c084fc' }
        ];
        return colors;
    }, []);

    const getSpeakerColor = (speaker, index = 0) => {
        const hash = (speaker || '').split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
        return speakerColors[(hash + index) % speakerColors.length];
    };

    // Collect all distinct speakers
    const distinctSpeakers = useMemo(() => {
        if (!meeting?.transcript?.segments) return [];
        const set = new Set();
        meeting.transcript.segments.forEach(seg => {
            if (seg.speaker) set.add(seg.speaker);
        });
        return Array.from(set);
    }, [meeting]);

    // Filter segments based on search query and speaker
    const filteredSegments = useMemo(() => {
        if (!meeting?.transcript?.segments) return [];
        return meeting.transcript.segments.filter(segment => {
            const matchesSpeaker = selectedSpeaker === 'all' || segment.speaker === selectedSpeaker;
            const matchesSearch = !searchQuery || segment.text.toLowerCase().includes(searchQuery.toLowerCase()) || (segment.speaker && segment.speaker.toLowerCase().includes(searchQuery.toLowerCase()));
            return matchesSpeaker && matchesSearch;
        });
    }, [meeting, selectedSpeaker, searchQuery]);

    const handleCopyTranscript = () => {
        if (!meeting?.transcript?.segments) return;
        const fullText = meeting.transcript.segments
            .map(s => `[${formatTimestamp(s.start)} - ${formatTimestamp(s.end)}] ${s.speaker}: ${s.text}`)
            .join('\n\n');
        navigator.clipboard.writeText(fullText).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2500);
        });
    };

    if (loading) {
        return (
            <div style={{ textAlign: 'center', marginTop: '6rem', color: 'var(--text-secondary)' }}>
                <RefreshCw size={36} className="spin" style={{ color: 'var(--accent-hover)', marginBottom: '1rem' }} />
                <p style={{ fontSize: '1rem' }}>Loading meeting intelligence...</p>
            </div>
        );
    }

    if (!meeting) {
        return (
            <div className="glass-panel" style={{ textAlign: 'center', margin: '4rem auto', maxWidth: '500px', padding: '3rem 2rem' }}>
                <AlertCircle size={48} style={{ color: 'var(--danger-color)', marginBottom: '1rem' }} />
                <h2 style={{ marginBottom: '0.5rem' }}>Meeting Not Found</h2>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>The requested meeting session could not be retrieved.</p>
                <Link to="/meetings" className="btn btn-primary">
                    <ArrowLeft size={16} /> Return to Meetings
                </Link>
            </div>
        );
    }

    const completedTasksCount = (meeting.tasks || []).filter(t => t.status === 'done').length;
    const totalTasksCount = (meeting.tasks || []).length;

    return (
        <div className="animate-fade-in delay-1" style={{ paddingBottom: '3rem' }}>
            {/* Top Navigation */}
            <div style={{ marginBottom: '1.5rem' }}>
                <Link 
                    to="/meetings" 
                    style={{ 
                        fontSize: '0.88rem', 
                        display: 'inline-flex', 
                        alignItems: 'center', 
                        gap: '0.5rem',
                        color: 'var(--text-secondary)',
                        padding: '0.4rem 0.8rem',
                        borderRadius: '8px',
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid var(--border-color)',
                        transition: 'all 0.2s ease'
                    }}
                >
                    <ArrowLeft size={15} /> Back to Sessions
                </Link>
            </div>

            {/* Header Hero Banner */}
            <div className="glass-panel" style={{ padding: '1.75rem 2rem', marginBottom: '2rem', borderRadius: '18px', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1.5rem' }}>
                    <div style={{ flex: '1 1 340px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                            <span className={`badge badge-${meeting.status}`} style={{ textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '0.75rem' }}>
                                {meeting.status}
                            </span>
                            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                                <Calendar size={13} /> {new Date(meeting.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                            </span>
                        </div>
                        <h1 style={{ fontSize: '1.85rem', fontWeight: 800, margin: '0 0 0.5rem 0', letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
                            {meeting.title}
                        </h1>
                        <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.9rem' }}>
                            AI Diarized Transcription & Action Item Extraction
                        </p>
                    </div>

                    {/* Quick Stat Badges */}
                    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                        <div style={{ padding: '0.65rem 1rem', background: 'rgba(15, 23, 42, 0.5)', borderRadius: '12px', border: '1px solid var(--border-color)', textAlign: 'center', minWidth: '90px' }}>
                            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent-hover)' }}>
                                {meeting.transcript?.segments?.length || 0}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                Segments
                            </div>
                        </div>

                        <div style={{ padding: '0.65rem 1rem', background: 'rgba(15, 23, 42, 0.5)', borderRadius: '12px', border: '1px solid var(--border-color)', textAlign: 'center', minWidth: '90px' }}>
                            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#38bdf8' }}>
                                {distinctSpeakers.length}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                Speakers
                            </div>
                        </div>

                        <div style={{ padding: '0.65rem 1rem', background: 'rgba(15, 23, 42, 0.5)', borderRadius: '12px', border: '1px solid var(--border-color)', textAlign: 'center', minWidth: '90px' }}>
                            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: completedTasksCount === totalTasksCount && totalTasksCount > 0 ? 'var(--success-color)' : 'var(--warning-color)' }}>
                                {completedTasksCount}/{totalTasksCount}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                Tasks Done
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {meeting.status === 'done' ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.85fr) minmax(0, 1.15fr)', gap: '1.75rem', alignItems: 'start' }}>
                    
                    {/* Transcript Column */}
                    <div className="glass-panel" style={{ padding: '1.75rem', borderRadius: '18px', border: '1px solid var(--border-color)' }}>
                        {/* Header & Controls */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(99, 102, 241, 0.15)', color: 'var(--accent-hover)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <MessageSquareQuote size={18} />
                                </div>
                                <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>Meeting Transcript</h3>
                            </div>

                            <button 
                                onClick={handleCopyTranscript}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.4rem',
                                    padding: '0.45rem 0.85rem',
                                    borderRadius: '8px',
                                    background: 'rgba(255, 255, 255, 0.05)',
                                    border: '1px solid var(--border-color)',
                                    color: copied ? 'var(--success-color)' : 'var(--text-secondary)',
                                    fontSize: '0.82rem',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s ease'
                                }}
                            >
                                {copied ? <Check size={14} /> : <Copy size={14} />}
                                {copied ? 'Copied Full Transcript!' : 'Copy Transcript'}
                            </button>
                        </div>

                        {/* Search & Speaker Filter Bar */}
                        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
                            <div style={{ position: 'relative', flex: '1 1 200px' }}>
                                <Search size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                                <input 
                                    type="text"
                                    placeholder="Search in transcript..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    style={{
                                        width: '100%',
                                        padding: '0.55rem 0.75rem 0.55rem 2.2rem',
                                        borderRadius: '8px',
                                        border: '1px solid var(--border-color)',
                                        background: 'var(--bg-secondary)',
                                        color: 'var(--text-primary)',
                                        fontSize: '0.85rem',
                                        outline: 'none',
                                        boxSizing: 'border-box'
                                    }}
                                />
                            </div>

                            {distinctSpeakers.length > 0 && (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', overflowX: 'auto', maxWidth: '100%', paddingBottom: '2px' }}>
                                    <button 
                                        onClick={() => setSelectedSpeaker('all')}
                                        style={{
                                            padding: '0.4rem 0.75rem',
                                            borderRadius: '6px',
                                            border: `1px solid ${selectedSpeaker === 'all' ? 'var(--accent-color)' : 'var(--border-color)'}`,
                                            background: selectedSpeaker === 'all' ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                                            color: selectedSpeaker === 'all' ? 'var(--accent-hover)' : 'var(--text-secondary)',
                                            fontSize: '0.8rem',
                                            cursor: 'pointer',
                                            whiteSpace: 'nowrap'
                                        }}
                                    >
                                        All
                                    </button>
                                    {distinctSpeakers.map((spk, idx) => {
                                        const c = getSpeakerColor(spk, idx);
                                        const isSelected = selectedSpeaker === spk;
                                        return (
                                            <button 
                                                key={spk}
                                                onClick={() => setSelectedSpeaker(spk)}
                                                style={{
                                                    padding: '0.4rem 0.75rem',
                                                    borderRadius: '6px',
                                                    border: `1px solid ${isSelected ? c.border : 'var(--border-color)'}`,
                                                    background: isSelected ? c.bg : 'transparent',
                                                    color: isSelected ? c.text : 'var(--text-secondary)',
                                                    fontSize: '0.8rem',
                                                    cursor: 'pointer',
                                                    whiteSpace: 'nowrap'
                                                }}
                                            >
                                                {spk}
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                        
                        {/* Segments Stream */}
                        <div className="transcript-box" style={{ maxHeight: '680px', overflowY: 'auto', paddingRight: '0.5rem' }}>
                            {filteredSegments.length > 0 ? (
                                filteredSegments.map((segment, idx) => {
                                    const col = getSpeakerColor(segment.speaker, idx);
                                    return (
                                        <div 
                                            className="segment" 
                                            key={idx}
                                            style={{
                                                padding: '1rem',
                                                marginBottom: '0.75rem',
                                                borderRadius: '12px',
                                                background: 'rgba(15, 23, 42, 0.4)',
                                                border: '1px solid rgba(255, 255, 255, 0.05)',
                                                transition: 'all 0.2s ease'
                                            }}
                                        >
                                            <div className="segment-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
                                                <span 
                                                    className="speaker-badge"
                                                    style={{
                                                        background: col.bg,
                                                        border: `1px solid ${col.border}`,
                                                        color: col.text,
                                                        fontWeight: 600,
                                                        padding: '0.2rem 0.6rem',
                                                        borderRadius: '6px',
                                                        fontSize: '0.8rem'
                                                    }}
                                                >
                                                    {segment.speaker || 'Speaker'}
                                                </span>
                                                <span 
                                                    className="timestamp"
                                                    style={{
                                                        fontSize: '0.78rem',
                                                        color: 'var(--text-secondary)',
                                                        fontVariantNumeric: 'tabular-nums',
                                                        display: 'inline-flex',
                                                        alignItems: 'center',
                                                        gap: '0.3rem'
                                                    }}
                                                >
                                                    <Clock size={12} /> {formatTimestamp(segment.start)} - {formatTimestamp(segment.end)}
                                                </span>
                                            </div>
                                            <div className="segment-text" style={{ fontSize: '0.92rem', lineHeight: 1.6, color: 'var(--text-primary)' }}>
                                                {segment.text}
                                            </div>
                                        </div>
                                    );
                                })
                            ) : (
                                <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-secondary)' }}>
                                    <p style={{ margin: 0, fontSize: '0.92rem' }}>
                                        {searchQuery || selectedSpeaker !== 'all' 
                                            ? 'No speech segments match your search criteria.' 
                                            : 'No transcript segments available for this meeting.'}
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Tasks Column */}
                    <div className="glass-panel" style={{ padding: '1.75rem', borderRadius: '18px', border: '1px solid var(--border-color)', position: 'sticky', top: '1rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.15)', color: 'var(--success-color)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <ListTodo size={18} />
                                </div>
                                <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>Action Items</h3>
                            </div>
                            <span style={{ fontSize: '0.78rem', padding: '0.2rem 0.55rem', borderRadius: '12px', background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}>
                                {meeting.tasks?.length || 0} Total
                            </span>
                        </div>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                            Extracted and assigned by AI models from conversational commitments.
                        </p>
                        
                        <div className="tasks-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                            {meeting.tasks && meeting.tasks.length > 0 ? (
                                meeting.tasks.map(task => {
                                    const isDone = task.status === 'done';
                                    return (
                                        <div 
                                            className="task-item" 
                                            key={task.id}
                                            style={{
                                                padding: '1rem',
                                                borderRadius: '12px',
                                                background: isDone ? 'rgba(16, 185, 129, 0.04)' : 'rgba(15, 23, 42, 0.4)',
                                                border: `1px solid ${isDone ? 'rgba(16, 185, 129, 0.25)' : 'rgba(255, 255, 255, 0.07)'}`,
                                                transition: 'all 0.2s ease'
                                            }}
                                        >
                                            <div className="task-header" style={{ marginBottom: '0.6rem' }}>
                                                <div 
                                                    className="task-desc" 
                                                    style={{ 
                                                        fontWeight: 500, 
                                                        fontSize: '0.92rem', 
                                                        color: isDone ? 'var(--text-secondary)' : 'var(--text-primary)',
                                                        textDecoration: isDone ? 'line-through' : 'none',
                                                        lineHeight: 1.45
                                                    }}
                                                >
                                                    {task.description}
                                                </div>
                                            </div>

                                            <div className="task-meta" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.8rem', marginBottom: '0.85rem', fontSize: '0.8rem' }}>
                                                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--text-secondary)' }}>
                                                    <User size={13} style={{ color: 'var(--accent-hover)' }} /> 
                                                    <strong style={{ color: 'var(--text-primary)' }}>{task.owner || 'Unassigned'}</strong>
                                                </span>
                                                {task.deadline && (
                                                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--warning-color)' }}>
                                                        <Calendar size={13} /> {task.deadline}
                                                    </span>
                                                )}
                                            </div>
                                            
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                <span className={`badge badge-${task.status}`} style={{ fontSize: '0.72rem', textTransform: 'capitalize' }}>
                                                    {task.status}
                                                </span>
                                                
                                                {!isDone && (
                                                    <button 
                                                        className="btn btn-secondary" 
                                                        style={{ 
                                                            padding: '0.35rem 0.75rem', 
                                                            fontSize: '0.78rem',
                                                            display: 'inline-flex',
                                                            alignItems: 'center',
                                                            gap: '0.35rem',
                                                            borderRadius: '6px'
                                                        }} 
                                                        onClick={() => markTaskDone(task.id)}
                                                    >
                                                        <Check size={13} /> Mark Done
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })
                            ) : (
                                <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--text-secondary)' }}>
                                    <CheckCircle2 size={40} style={{ marginBottom: '0.75rem', opacity: 0.4, color: 'var(--success-color)' }} />
                                    <p style={{ fontSize: '0.9rem', margin: 0 }}>No action items extracted for this session.</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            ) : meeting.status === 'failed' ? (
                <div className="glass-panel" style={{ textAlign: 'center', padding: '4rem 2rem', borderRadius: '18px', border: '1px solid rgba(239, 68, 68, 0.25)' }}>
                    <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger-color)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem' }}>
                        <AlertCircle size={36} />
                    </div>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>Processing Failed</h2>
                    <p style={{ color: 'var(--text-secondary)', maxWidth: '450px', margin: '0 auto 1.5rem' }}>
                        An unexpected issue occurred while analyzing this meeting. You can re-upload the audio or re-dispatch the bot.
                    </p>
                    <Link to="/upload" className="btn btn-primary">
                        Try Again in Upload Center
                    </Link>
                </div>
            ) : (
                <div className="glass-panel" style={{ textAlign: 'center', padding: '4rem 2rem', borderRadius: '18px' }}>
                    <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: 'rgba(99, 102, 241, 0.1)', color: 'var(--accent-hover)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem' }}>
                        <RefreshCw size={32} className="spin" />
                    </div>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>Processing Intelligence...</h2>
                    <p style={{ color: 'var(--text-secondary)', maxWidth: '450px', margin: '0 auto 1.5rem' }}>
                        Our speech models are transcribing speech, distinguishing speakers, and extracting key deliverables.
                    </p>
                    <button 
                        className="btn btn-secondary" 
                        onClick={fetchMeeting}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
                    >
                        <RefreshCw size={14} /> Refresh Status
                    </button>
                </div>
            )}
        </div>
    );
}
