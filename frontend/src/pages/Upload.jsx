import React, { useState, useRef, useContext, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { 
    UploadCloud, 
    Hourglass, 
    Mic, 
    Wand2, 
    CheckCircle2, 
    RefreshCw, 
    XCircle, 
    Bot, 
    Calendar, 
    Sparkles, 
    FileSpreadsheet, 
    X, 
    Link2, 
    Clock, 
    Users, 
    FileAudio, 
    ArrowRight,
    AlertCircle,
    CalendarCheck
} from 'lucide-react';
import { AuthContext } from '../context/AuthContext';

export default function Upload() {
    const [file, setFile] = useState(null);
    const [recordedDate, setRecordedDate] = useState(new Date().toISOString().split('T')[0]);
    const [status, setStatus] = useState('idle'); // idle, uploading, pending, transcribing, extracting, done, failed, scheduled
    const [meetingId, setMeetingId] = useState(null);
    const fileInputRef = useRef(null);
    const { token } = useContext(AuthContext);

    const [activeTab, setActiveTab] = useState('upload'); // 'upload' or 'bot'
    const [meetUrl, setMeetUrl] = useState('');
    const [scheduledTime, setScheduledTime] = useState('');
    const [botDuration, setBotDuration] = useState(60);
    const [botStatus, setBotStatus] = useState('idle');
    const [botEmail, setBotEmail] = useState('');
    const [botPassword, setBotPassword] = useState('');
    const [csvFile, setCsvFile] = useState(null);
    const [fetchedAttendees, setFetchedAttendees] = useState([]);
    const [calendarConnected, setCalendarConnected] = useState(false);
    const BOT_EMAIL = 'meettrack-bot@gmail.com'; // Shown to user as a fallback tip

    // Check if calendar is connected
    useEffect(() => {
        api.get('/calendar/status')
            .then(res => setCalendarConnected(res.data.connected))
            .catch(() => {});
    }, []);

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            setFile(e.target.files[0]);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            setFile(e.dataTransfer.files[0]);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!file) return;

        setStatus('uploading');
        const formData = new FormData();
        formData.append('file', file);
        formData.append('recorded_date', recordedDate);
        if (csvFile) {
            formData.append('participants_csv', csvFile);
        }

        try {
            const res = await api.post('/meetings/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            setMeetingId(res.data.meeting_id);
            setStatus('pending');
            pollStatus(res.data.meeting_id);
        } catch (err) {
            console.error(err);
            setStatus('idle');
            alert('Upload failed: ' + err.message);
        }
    };

    const handleBotSubmit = async (e) => {
        e.preventDefault();
        if (!meetUrl) return;

        setBotStatus('dispatching');
        
        const formData = new FormData();
        formData.append('meet_url', meetUrl);
        if (botEmail && botPassword) {
            formData.append('bot_email', botEmail);
            formData.append('bot_password', botPassword);
        }
        if (scheduledTime) {
            formData.append('scheduled_time', new Date(scheduledTime).toISOString());
        }
        if (csvFile) {
            formData.append('participants_csv', csvFile);
        }

        try {
            const res = await api.post('/meetings/bot/join', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            setMeetingId(res.data.meeting_id);
            if (res.data.scheduled) {
                setStatus('scheduled');
            } else {
                setStatus('pending');
            }
            setActiveTab('upload'); 
            pollStatus(res.data.meeting_id);
        } catch (err) {
            console.error(err);
            setBotStatus('idle');
            alert(err.response?.data?.detail || 'Bot dispatch failed: ' + err.message);
        }
    };

    const handleFetchCalendar = async () => {
        try {
            const res = await api.get('/calendar/fetch_upcoming');
            if (res.data.status === 'missing_credentials') {
                alert(res.data.instructions);
                return;
            }
            if (res.data.status === 'error') {
                alert(res.data.message);
                return;
            }
            if (res.data.meet_url) {
                setMeetUrl(res.data.meet_url);
                setFetchedAttendees(res.data.attendees || []);
                if (res.data.start_time) {
                    const localDate = new Date(res.data.start_time);
                    const tzoffset = (new Date()).getTimezoneOffset() * 60000;
                    const localISOTime = new Date(localDate - tzoffset).toISOString().slice(0, 16);
                    setScheduledTime(localISOTime);
                }
                alert('Successfully fetched upcoming meeting from Calendar!');
            }
        } catch (err) {
            console.error(err);
            alert('Failed to fetch from calendar: ' + (err.response?.data?.message || err.message));
        }
    };

    const pollStatus = async (id) => {
        try {
            const res = await api.get(`/meetings/${id}`);
            setStatus(res.data.status);
            
            if (res.data.status === 'scheduled') {
                // Poll slower if waiting for a scheduled meeting (every 30s)
                setTimeout(() => pollStatus(id), 30000);
            } else if (res.data.status !== 'done' && res.data.status !== 'failed') {
                // Poll fast if actively processing (every 5s)
                setTimeout(() => pollStatus(id), 5000);
            }
        } catch (err) {
            console.error('Polling error', err);
        }
    };

    const stepOrder = ['pending', 'processing', 'extracting', 'done'];
    const currentStepIndex = stepOrder.indexOf(status);

    const formatFileSize = (bytes) => {
        if (!bytes) return '';
        const mb = bytes / (1024 * 1024);
        return mb >= 1 ? `${mb.toFixed(1)} MB` : `${(bytes / 1024).toFixed(0)} KB`;
    };

    return (
        <div className="animate-fade-in delay-1" style={{ maxWidth: '820px', margin: '0 auto', paddingBottom: '3rem' }}>
            {/* Page Header */}
            <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.35rem 0.85rem', borderRadius: '999px', background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.25)', color: 'var(--accent-hover)', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                    <Sparkles size={14} /> AI Meeting Assistant
                </div>
                <h1 style={{ fontSize: '2rem', fontWeight: 800, letterSpacing: '-0.02em', margin: '0 0 0.5rem 0' }}>
                    Process Meeting
                </h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', maxWidth: '520px', margin: '0 auto' }}>
                    Upload an audio recording or dispatch our automated bot directly into a live Google Meet.
                </p>
            </div>

            {/* Tab Switcher */}
            {(status === 'idle' || status === 'uploading') && (
                <div style={{
                    display: 'flex',
                    background: 'rgba(15, 23, 42, 0.6)',
                    padding: '0.35rem',
                    borderRadius: '14px',
                    border: '1px solid var(--border-color)',
                    width: 'fit-content',
                    margin: '0 auto 1.75rem',
                    backdropFilter: 'blur(10px)'
                }}>
                    <button 
                        type="button"
                        onClick={() => setActiveTab('upload')}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.65rem 1.4rem',
                            borderRadius: '10px',
                            border: 'none',
                            fontSize: '0.88rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                            background: activeTab === 'upload' ? 'linear-gradient(135deg, #6366f1, #4f46e5)' : 'transparent',
                            color: activeTab === 'upload' ? '#ffffff' : 'var(--text-secondary)',
                            boxShadow: activeTab === 'upload' ? '0 4px 12px rgba(99, 102, 241, 0.35)' : 'none'
                        }}
                    >
                        <UploadCloud size={16} /> Upload Recording
                    </button>
                    <button 
                        type="button"
                        onClick={() => setActiveTab('bot')}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.65rem 1.4rem',
                            borderRadius: '10px',
                            border: 'none',
                            fontSize: '0.88rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                            background: activeTab === 'bot' ? 'linear-gradient(135deg, #6366f1, #4f46e5)' : 'transparent',
                            color: activeTab === 'bot' ? '#ffffff' : 'var(--text-secondary)',
                            boxShadow: activeTab === 'bot' ? '0 4px 12px rgba(99, 102, 241, 0.35)' : 'none'
                        }}
                    >
                        <Bot size={16} /> Send Live Bot
                    </button>
                </div>
            )}

            {/* Main Content Box */}
            <div className="glass-panel" style={{ padding: '2rem', borderRadius: '18px', border: '1px solid var(--border-color)', boxShadow: '0 12px 32px rgba(0,0,0,0.25)' }}>
                {status === 'idle' || status === 'uploading' ? (
                    activeTab === 'upload' ? (
                        /* ================== TAB 1: FILE UPLOAD ================== */
                        <form onSubmit={handleSubmit}>
                            {/* Drop Area */}
                            <div 
                                className="upload-area" 
                                onDrop={handleDrop} 
                                onDragOver={(e) => e.preventDefault()}
                                onClick={() => fileInputRef.current?.click()}
                                style={{
                                    border: `2px dashed ${file ? 'var(--accent-color)' : 'rgba(255, 255, 255, 0.15)'}`,
                                    borderRadius: '14px',
                                    padding: '2.5rem 1.5rem',
                                    textAlign: 'center',
                                    cursor: 'pointer',
                                    background: file ? 'rgba(99, 102, 241, 0.04)' : 'rgba(15, 23, 42, 0.4)',
                                    transition: 'all 0.25s ease'
                                }}
                            >
                                <div style={{
                                    width: '56px',
                                    height: '56px',
                                    borderRadius: '14px',
                                    background: file ? 'rgba(99, 102, 241, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                                    color: file ? 'var(--accent-hover)' : 'var(--text-secondary)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    margin: '0 auto 1rem'
                                }}>
                                    {file ? <FileAudio size={28} /> : <UploadCloud size={28} />}
                                </div>

                                {file ? (
                                    <div>
                                        <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                                            {file.name}
                                        </h3>
                                        <p style={{ color: 'var(--accent-hover)', fontSize: '0.85rem', marginBottom: '0.5rem', fontWeight: 500 }}>
                                            {formatFileSize(file.size)} &bull; Ready to process
                                        </p>
                                        <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textDecoration: 'underline' }}>
                                            Click or drop to replace file
                                        </span>
                                    </div>
                                ) : (
                                    <div>
                                        <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
                                            Drag & drop your recording here
                                        </h3>
                                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', margin: '0 0 0.5rem' }}>
                                            or <span style={{ color: 'var(--accent-hover)', fontWeight: 600 }}>browse files</span> from your computer
                                        </p>
                                        <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', opacity: 0.7, margin: 0 }}>
                                            Supported: .mp3, .wav, .flac, .mp4, .m4a
                                        </p>
                                    </div>
                                )}

                                <input 
                                    type="file" 
                                    ref={fileInputRef}
                                    onChange={handleFileChange}
                                    accept="audio/*,video/mp4" 
                                    style={{ display: 'none' }} 
                                />
                            </div>

                            {/* Meeting Metadata Options */}
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginTop: '1.75rem' }}>
                                {/* Date Picker */}
                                <div>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', marginBottom: '0.5rem', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        <Calendar size={14} /> Meeting Date
                                    </label>
                                    <input 
                                        type="date" 
                                        value={recordedDate} 
                                        onChange={(e) => setRecordedDate(e.target.value)}
                                        style={{
                                            width: '100%',
                                            padding: '0.7rem 0.9rem',
                                            borderRadius: '10px',
                                            border: '1px solid var(--border-color)',
                                            background: 'var(--bg-secondary)',
                                            color: 'var(--text-primary)',
                                            fontSize: '0.9rem',
                                            outline: 'none',
                                            boxSizing: 'border-box'
                                        }}
                                    />
                                </div>

                                {/* CSV Upload for Participants */}
                                <div>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', marginBottom: '0.5rem', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        <FileSpreadsheet size={14} /> Participants CSV <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0, opacity: 0.6 }}>(optional)</span>
                                    </label>
                                    <div
                                        onClick={() => document.getElementById('csv-upload-input-manual')?.click()}
                                        onDrop={(e) => { e.preventDefault(); if (e.dataTransfer.files[0]) setCsvFile(e.dataTransfer.files[0]); }}
                                        onDragOver={(e) => e.preventDefault()}
                                        style={{
                                            border: `1px dashed ${csvFile ? 'var(--accent-color)' : 'var(--border-color)'}`,
                                            borderRadius: '10px',
                                            padding: '0.65rem 0.85rem',
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'space-between',
                                            background: csvFile ? 'rgba(99, 102, 241, 0.08)' : 'var(--bg-secondary)',
                                            minHeight: '44px',
                                            boxSizing: 'border-box'
                                        }}
                                    >
                                        <span style={{ fontSize: '0.85rem', color: csvFile ? 'var(--text-primary)' : 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {csvFile ? csvFile.name : 'Drop CSV (Name, Email)'}
                                        </span>
                                        {csvFile ? (
                                            <button 
                                                type="button" 
                                                onClick={(e) => { e.stopPropagation(); setCsvFile(null); }}
                                                style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '2px' }}
                                            >
                                                <X size={15} />
                                            </button>
                                        ) : (
                                            <FileSpreadsheet size={15} color="var(--text-secondary)" style={{ opacity: 0.6 }} />
                                        )}
                                    </div>
                                    <input 
                                        id="csv-upload-input-manual" 
                                        type="file" 
                                        accept=".csv" 
                                        onChange={(e) => setCsvFile(e.target.files[0])} 
                                        style={{ display: 'none' }} 
                                    />
                                </div>
                            </div>

                            {/* Submit Button */}
                            <div style={{ marginTop: '2rem', textAlign: 'center' }}>
                                <button 
                                    type="submit" 
                                    className="btn btn-primary" 
                                    disabled={!file || status === 'uploading'}
                                    style={{
                                        width: '100%',
                                        padding: '0.85rem',
                                        fontSize: '0.98rem',
                                        fontWeight: 600,
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '0.6rem',
                                        opacity: (!file || status === 'uploading') ? 0.6 : 1,
                                        cursor: (!file || status === 'uploading') ? 'not-allowed' : 'pointer'
                                    }}
                                >
                                    {status === 'uploading' ? (
                                        <>
                                            <RefreshCw className="spin" size={18} /> Uploading & Processing...
                                        </>
                                    ) : (
                                        <>
                                            <Wand2 size={18} /> Start AI Transcription & Analysis
                                        </>
                                    )}
                                </button>
                            </div>
                        </form>
                    ) : (
                        /* ================== TAB 2: LIVE BOT ================== */
                        <form onSubmit={handleBotSubmit}>
                            {/* Calendar Integration Notice */}
                            {!calendarConnected && (
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'flex-start',
                                    gap: '0.75rem',
                                    background: 'rgba(99, 102, 241, 0.08)',
                                    border: '1px solid rgba(99, 102, 241, 0.25)',
                                    borderRadius: '12px',
                                    padding: '0.85rem 1rem',
                                    marginBottom: '1.5rem'
                                }}>
                                    <CalendarCheck size={18} color="var(--accent-hover)" style={{ marginTop: '2px', flexShrink: 0 }} />
                                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                                        <strong style={{ color: 'var(--text-primary)' }}>Google Calendar Sync:</strong> You can automatically detect upcoming Google Meets and attendee lists.{' '}
                                        <button 
                                            type="button" 
                                            onClick={() => window.location.href = `${api.defaults.baseURL}/calendar/auth?token=${token}&redirect_to=${encodeURIComponent(window.location.origin)}`} 
                                            style={{ background: 'none', border: 'none', color: 'var(--accent-hover)', cursor: 'pointer', padding: 0, fontSize: '0.85rem', fontWeight: 600, textDecoration: 'underline' }}
                                        >
                                            Connect Calendar &rarr;
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* Section 1: Meeting URL */}
                            <div style={{ marginBottom: '1.5rem' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', marginBottom: '0.5rem', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                    <Link2 size={14} /> Google Meet URL <span style={{ color: 'var(--danger-color)' }}>*</span>
                                </label>
                                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                    <input
                                        type="url"
                                        placeholder="https://meet.google.com/xxx-xxxx-xxx"
                                        value={meetUrl}
                                        onChange={(e) => setMeetUrl(e.target.value)}
                                        style={{
                                            flex: '1 1 260px',
                                            padding: '0.7rem 0.9rem',
                                            borderRadius: '10px',
                                            border: '1px solid var(--border-color)',
                                            background: 'var(--bg-secondary)',
                                            color: 'var(--text-primary)',
                                            fontSize: '0.9rem',
                                            outline: 'none'
                                        }}
                                        required
                                    />
                                    <button 
                                        type="button" 
                                        title="Connect Google Calendar" 
                                        onClick={() => window.location.href = `${api.defaults.baseURL}/calendar/auth?token=${token}&redirect_to=${encodeURIComponent(window.location.origin)}`}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.4rem',
                                            padding: '0.7rem 0.9rem',
                                            borderRadius: '10px',
                                            border: '1px solid var(--border-color)',
                                            background: 'var(--bg-secondary)',
                                            color: 'var(--text-secondary)',
                                            cursor: 'pointer',
                                            fontSize: '0.82rem',
                                            fontWeight: 500,
                                            whiteSpace: 'nowrap',
                                            transition: 'all 0.2s'
                                        }}
                                    >
                                        <Calendar size={14} /> Connect Calendar
                                    </button>
                                    <button 
                                        type="button" 
                                        title="Auto-fill from Calendar" 
                                        onClick={handleFetchCalendar}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.4rem',
                                            padding: '0.7rem 0.9rem',
                                            borderRadius: '10px',
                                            border: '1px solid rgba(99, 102, 241, 0.4)',
                                            background: 'rgba(99, 102, 241, 0.12)',
                                            color: 'var(--accent-hover)',
                                            cursor: 'pointer',
                                            fontSize: '0.82rem',
                                            fontWeight: 600,
                                            whiteSpace: 'nowrap',
                                            transition: 'all 0.2s'
                                        }}
                                    >
                                        <Sparkles size={14} /> Auto-fill
                                    </button>
                                </div>
                            </div>

                            {/* Section 2: Scheduled Time & Attendees */}
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
                                <div>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', marginBottom: '0.5rem', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        <Clock size={14} /> Scheduled Time <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0, opacity: 0.6 }}>(optional)</span>
                                    </label>
                                    <input
                                        type="datetime-local"
                                        value={scheduledTime}
                                        onChange={(e) => setScheduledTime(e.target.value)}
                                        style={{
                                            width: '100%',
                                            padding: '0.7rem 0.9rem',
                                            borderRadius: '10px',
                                            border: '1px solid var(--border-color)',
                                            background: 'var(--bg-secondary)',
                                            color: 'var(--text-primary)',
                                            fontSize: '0.9rem',
                                            outline: 'none',
                                            boxSizing: 'border-box'
                                        }}
                                    />
                                    {scheduledTime && (
                                        <p style={{ margin: '0.4rem 0 0', fontSize: '0.8rem', color: 'var(--accent-hover)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                            <Clock size={12} /> Bot will auto-launch 2 min before this time
                                        </p>
                                    )}
                                </div>

                                <div>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', marginBottom: '0.5rem', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        <FileSpreadsheet size={14} /> Participants CSV <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0, opacity: 0.6 }}>(optional)</span>
                                    </label>
                                    <div
                                        onClick={() => document.getElementById('csv-upload-input-bot')?.click()}
                                        onDrop={(e) => { e.preventDefault(); if (e.dataTransfer.files[0]) setCsvFile(e.dataTransfer.files[0]); }}
                                        onDragOver={(e) => e.preventDefault()}
                                        style={{
                                            border: `1px dashed ${csvFile ? 'var(--accent-color)' : 'var(--border-color)'}`,
                                            borderRadius: '10px',
                                            padding: '0.65rem 0.85rem',
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'space-between',
                                            background: csvFile ? 'rgba(99, 102, 241, 0.08)' : 'var(--bg-secondary)',
                                            minHeight: '44px',
                                            boxSizing: 'border-box'
                                        }}
                                    >
                                        <span style={{ fontSize: '0.85rem', color: csvFile ? 'var(--text-primary)' : 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {csvFile ? csvFile.name : 'Drop CSV (Name, Email)'}
                                        </span>
                                        {csvFile ? (
                                            <button 
                                                type="button" 
                                                onClick={(e) => { e.stopPropagation(); setCsvFile(null); }}
                                                style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '2px' }}
                                            >
                                                <X size={15} />
                                            </button>
                                        ) : (
                                            <FileSpreadsheet size={15} color="var(--text-secondary)" style={{ opacity: 0.6 }} />
                                        )}
                                    </div>
                                    <input 
                                        id="csv-upload-input-bot" 
                                        type="file" 
                                        accept=".csv" 
                                        onChange={(e) => setCsvFile(e.target.files[0])} 
                                        style={{ display: 'none' }} 
                                    />
                                </div>
                            </div>

                            {/* Attendees pill list */}
                            {fetchedAttendees.length > 0 && (
                                <div style={{ marginBottom: '1.5rem', background: 'rgba(99, 102, 241, 0.06)', border: '1px solid rgba(99, 102, 241, 0.2)', borderRadius: '12px', padding: '0.85rem 1rem' }}>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem', fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-hover)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        <Users size={14} /> Detected Attendees ({fetchedAttendees.length})
                                    </label>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                                        {fetchedAttendees.map((a, i) => (
                                            <span key={i} style={{ padding: '0.25rem 0.65rem', background: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.3)', borderRadius: '20px', fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                                                {a.name || a.email}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Submit Bot Button */}
                            <button 
                                type="submit" 
                                className="btn btn-primary" 
                                style={{ width: '100%', padding: '0.85rem', fontSize: '0.98rem', fontWeight: 600, justifyContent: 'center', gap: '0.6rem' }} 
                                disabled={botStatus === 'dispatching'}
                            >
                                {botStatus === 'dispatching' ? (
                                    <>
                                        <RefreshCw className="spin" size={18} /> Dispatching Bot...
                                    </>
                                ) : (
                                    <>
                                        <Bot size={18} /> {scheduledTime ? 'Schedule Meeting Bot' : 'Dispatch Live Bot Now'}
                                    </>
                                )}
                            </button>
                        </form>
                    )
                ) : (
                    /* ================== PROCESSING / SCHEDULED STATUS ================== */
                    <div style={{ padding: '1rem 0' }}>
                        {status === 'scheduled' ? (
                            <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
                                <div style={{
                                    width: '64px',
                                    height: '64px',
                                    borderRadius: '50%',
                                    background: 'rgba(99, 102, 241, 0.15)',
                                    color: 'var(--accent-hover)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    margin: '0 auto 1.25rem',
                                    border: '1px solid rgba(99, 102, 241, 0.3)'
                                }}>
                                    <CalendarCheck size={32} />
                                </div>
                                <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.35rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                                    Meeting Scheduled Successfully
                                </h3>
                                <p style={{ color: 'var(--text-secondary)', margin: '0 0 1rem 0', fontSize: '0.92rem' }}>
                                    The bot will automatically launch and join your Google Meet 2 minutes prior to the start time.
                                </p>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0, opacity: 0.7 }}>
                                    You can safely navigate away or review scheduled sessions on your Dashboard.
                                </p>
                            </div>
                        ) : (
                            <div style={{ maxWidth: '460px', margin: '0 auto' }}>
                                <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                                    <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: '0 0 0.4rem 0' }}>
                                        {status === 'failed' ? 'Processing Failed' : status === 'done' ? 'Analysis Complete' : 'AI Engine In Progress'}
                                    </h3>
                                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', margin: 0 }}>
                                        {status === 'failed' 
                                            ? 'An issue occurred during transcription. You can try again.'
                                            : status === 'done'
                                            ? 'Transcript, diarization, and action items are ready.'
                                            : 'Please keep this page open while our models process the audio.'}
                                    </p>
                                </div>

                                {/* Step Timeline */}
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                    {[
                                        { id: 'pending', label: 'Queued in Processing Pipeline', icon: Hourglass },
                                        { id: 'processing', label: 'Transcribing & Voice Diarization', icon: Mic },
                                        { id: 'extracting', label: 'Extracting Action Items & Insights', icon: Wand2 },
                                        { id: 'done', label: 'Processing Finalized', icon: CheckCircle2 }
                                    ].map((step, idx) => {
                                        const isDone = currentStepIndex > idx || status === 'done';
                                        const isCurrent = currentStepIndex === idx && status !== 'done' && status !== 'failed';
                                        const StepIcon = step.icon;

                                        return (
                                            <div 
                                                key={step.id}
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '1rem',
                                                    padding: '0.85rem 1rem',
                                                    borderRadius: '12px',
                                                    background: isCurrent 
                                                        ? 'rgba(99, 102, 241, 0.1)' 
                                                        : isDone 
                                                        ? 'rgba(16, 185, 129, 0.05)' 
                                                        : 'rgba(255, 255, 255, 0.02)',
                                                    border: `1px solid ${isCurrent ? 'rgba(99, 102, 241, 0.3)' : isDone ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.05)'}`,
                                                    transition: 'all 0.2s ease'
                                                }}
                                            >
                                                <div style={{
                                                    width: '32px',
                                                    height: '32px',
                                                    borderRadius: '8px',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    background: isDone 
                                                        ? 'rgba(16, 185, 129, 0.15)' 
                                                        : isCurrent 
                                                        ? 'rgba(99, 102, 241, 0.2)' 
                                                        : 'rgba(255, 255, 255, 0.05)',
                                                    color: isDone 
                                                        ? 'var(--success-color)' 
                                                        : isCurrent 
                                                        ? 'var(--accent-hover)' 
                                                        : 'var(--text-secondary)'
                                                }}>
                                                    {isCurrent ? (
                                                        <RefreshCw className="spin" size={16} />
                                                    ) : isDone ? (
                                                        <CheckCircle2 size={16} />
                                                    ) : (
                                                        <StepIcon size={16} />
                                                    )}
                                                </div>
                                                <span style={{ 
                                                    fontSize: '0.9rem', 
                                                    fontWeight: isCurrent || isDone ? 600 : 400,
                                                    color: isDone ? 'var(--text-primary)' : isCurrent ? 'var(--accent-hover)' : 'var(--text-secondary)'
                                                }}>
                                                    {step.label}
                                                </span>
                                            </div>
                                        );
                                    })}

                                    {status === 'failed' && (
                                        <div style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '1rem',
                                            padding: '0.85rem 1rem',
                                            borderRadius: '12px',
                                            background: 'rgba(239, 68, 68, 0.1)',
                                            border: '1px solid rgba(239, 68, 68, 0.25)',
                                            color: 'var(--danger-color)'
                                        }}>
                                            <XCircle size={20} />
                                            <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>
                                                Meeting Processing Failed
                                            </span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Navigation / Action Footer */}
                        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginTop: '2.5rem' }}>
                            {status === 'done' && meetingId && (
                                <Link 
                                    to={`/meetings/${meetingId}/view`} 
                                    className="btn btn-primary"
                                    style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 1.4rem' }}
                                >
                                    Open Meeting Studio <ArrowRight size={16} />
                                </Link>
                            )}
                            {(status === 'done' || status === 'failed') && (
                                <button 
                                    className="btn btn-secondary" 
                                    onClick={() => { setStatus('idle'); setBotStatus('idle'); setFile(null); setCsvFile(null); }}
                                    style={{ padding: '0.75rem 1.4rem' }}
                                >
                                    Process Another Meeting
                                </button>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
