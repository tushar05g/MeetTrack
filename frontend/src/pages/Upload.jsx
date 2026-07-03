import React, { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { UploadCloud, Hourglass, Mic, Wand2, CheckCircle2, RefreshCw, XCircle } from 'lucide-react';

export default function Upload() {
    const [file, setFile] = useState(null);
    const [recordedDate, setRecordedDate] = useState(new Date().toISOString().split('T')[0]);
    const [status, setStatus] = useState('idle'); // idle, uploading, pending, transcribing, extracting, done, failed
    const [meetingId, setMeetingId] = useState(null);
    const fileInputRef = useRef(null);

    const [activeTab, setActiveTab] = useState('upload'); // 'upload' or 'bot'
    const [meetUrl, setMeetUrl] = useState('');
    const [scheduledTime, setScheduledTime] = useState('');
    const [botDuration, setBotDuration] = useState(60);
    const [botStatus, setBotStatus] = useState('idle');
    const [csvFile, setCsvFile] = useState(null);
    const [fetchedAttendees, setFetchedAttendees] = useState([]);

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
        formData.append('duration_seconds', botDuration);
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
            setStatus('pending'); 
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
            alert('Failed to fetch from calendar');
        }
    };

    const pollStatus = async (id) => {
        try {
            const res = await api.get(`/meetings/${id}`);
            setStatus(res.data.status);
            
            if (res.data.status !== 'done' && res.data.status !== 'failed') {
                setTimeout(() => pollStatus(id), 5000);
            }
        } catch (err) {
            console.error('Polling error', err);
        }
    };

    const steps = ['pending', 'processing', 'extracting', 'done'];
    const currentStepIndex = steps.indexOf(status);

    const isProcessing = ['pending', 'processing', 'extracting', 'uploading'].includes(status);

    return (
        <div className="animate-fade-in delay-1" style={{ maxWidth: '800px', margin: '0 auto' }}>
            <h1>Process Meeting</h1>
            <p>Upload a recording or send our Bot to a live Google Meet.</p>

            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', justifyContent: 'center' }}>
                <button 
                    className={`btn ${activeTab === 'upload' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveTab('upload')}
                >
                    Upload File
                </button>
                <button 
                    className={`btn ${activeTab === 'bot' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveTab('bot')}
                >
                    Send Live Bot
                </button>
            </div>

            <div className="glass-panel" style={{ marginTop: '1rem' }}>
                {status === 'idle' || status === 'uploading' ? (
                    activeTab === 'upload' ? (
                        <form onSubmit={handleSubmit}>
                        <div 
                            className="upload-area" 
                            onDrop={handleDrop} 
                            onDragOver={(e) => e.preventDefault()}
                            onClick={() => fileInputRef.current.click()}
                        >
                            <UploadCloud className="upload-icon" size={48} />
                            <h3 style={{ marginBottom: '0.5rem' }}>Drag and drop your file here</h3>
                            <p>or click to browse from your computer</p>
                            <p style={{ fontSize: '0.8rem', marginBottom: 0 }}>Supported formats: .mp3, .wav, .flac, .mp4</p>
                            <input 
                                type="file" 
                                ref={fileInputRef}
                                onChange={handleFileChange}
                                accept="audio/*,video/mp4" 
                                style={{ display: 'none' }} 
                            />
                        </div>
                        
                        <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, color: 'var(--text-secondary)' }}>Meeting Date:</label>
                            <input 
                                type="date" 
                                value={recordedDate} 
                                onChange={(e) => setRecordedDate(e.target.value)}
                                style={{ padding: '0.5rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', outline: 'none', minWidth: '200px' }}
                            />
                        </div>

                        {file && (
                            <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
                                <p style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
                                    Selected file: <span style={{ color: 'var(--accent-color)' }}>{file.name}</span>
                                </p>
                                <button type="submit" className="btn btn-primary" style={{ marginTop: '1rem' }} disabled={status === 'uploading'}>
                                    {status === 'uploading' ? <RefreshCw className="spin" /> : <UploadCloud />} 
                                    {status === 'uploading' ? ' Uploading...' : ' Process Meeting'}
                                </button>
                            </div>
                        )}
                    </form>
                    ) : (
                    <form onSubmit={handleBotSubmit}>
                        {/* Header */}
                        <div style={{ marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border-color)' }}>
                            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Send Bot to Google Meet</h3>
                            <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>The bot will join the meeting and record audio automatically.</p>
                        </div>

                        {/* Section 1: Meeting URL */}
                        <div style={{ marginBottom: '1.25rem' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                🔗 Meeting URL
                            </label>
                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                <input
                                    type="url"
                                    placeholder="https://meet.google.com/xxx-xxxx-xxx"
                                    value={meetUrl}
                                    onChange={(e) => setMeetUrl(e.target.value)}
                                    style={{ flex: 1, padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.9rem', outline: 'none' }}
                                    required
                                />
                                <button type="button" title="Connect Google Calendar" onClick={() => window.location.href = 'http://localhost:8000/calendar/auth'}
                                    style={{ padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-secondary)', cursor: 'pointer', whiteSpace: 'nowrap', fontSize: '0.82rem', fontWeight: 500, transition: 'all 0.2s' }}
                                    onMouseOver={e => e.currentTarget.style.borderColor = 'var(--accent-color)'}
                                    onMouseOut={e => e.currentTarget.style.borderColor = 'var(--border-color)'}
                                >
                                    📅 Connect Calendar
                                </button>
                                <button type="button" title="Auto-fill from Calendar" onClick={handleFetchCalendar}
                                    style={{ padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid var(--accent-color)', background: 'rgba(139,92,246,0.1)', color: 'var(--accent-color)', cursor: 'pointer', whiteSpace: 'nowrap', fontSize: '0.82rem', fontWeight: 500, transition: 'all 0.2s' }}
                                    onMouseOver={e => e.currentTarget.style.background = 'rgba(139,92,246,0.2)'}
                                    onMouseOut={e => e.currentTarget.style.background = 'rgba(139,92,246,0.1)'}
                                >
                                    ✨ Auto-fill
                                </button>
                            </div>
                        </div>

                        {/* Section 2: Schedule + Duration side by side */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
                            <div>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                    🕐 Scheduled Time <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0, marginLeft: '0.25rem', color: 'var(--text-secondary)', opacity: 0.7 }}>(optional)</span>
                                </label>
                                <input
                                    type="datetime-local"
                                    value={scheduledTime}
                                    onChange={(e) => setScheduledTime(e.target.value)}
                                    style={{ width: '100%', padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.9rem', outline: 'none', boxSizing: 'border-box' }}
                                />
                                {scheduledTime && (
                                    <p style={{ margin: '0.35rem 0 0', fontSize: '0.78rem', color: 'var(--accent-color)' }}>
                                        ⏰ Bot will auto-launch 2 min before this time
                                    </p>
                                )}
                            </div>
                            <div>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                    ⏱ Record Duration
                                </label>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <input
                                        type="number"
                                        value={botDuration}
                                        min={10}
                                        onChange={(e) => setBotDuration(e.target.value)}
                                        style={{ width: '100px', padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.9rem', outline: 'none' }}
                                    />
                                    <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>seconds</span>
                                </div>
                                <p style={{ margin: '0.35rem 0 0', fontSize: '0.78rem', color: 'var(--text-secondary)', opacity: 0.7 }}>
                                    ~{Math.floor(botDuration / 60)}m {botDuration % 60}s of recording
                                </p>
                            </div>
                        </div>

                        {/* Section 3: Attendees (fetched) */}
                        {fetchedAttendees.length > 0 && (
                            <div style={{ marginBottom: '1.25rem', background: 'rgba(139,92,246,0.05)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: '10px', padding: '0.85rem 1rem' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.6rem', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                    👥 Detected Attendees ({fetchedAttendees.length})
                                </label>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                                    {fetchedAttendees.map((a, i) => (
                                        <span key={i} style={{ padding: '0.25rem 0.65rem', background: 'rgba(139,92,246,0.15)', border: '1px solid rgba(139,92,246,0.3)', borderRadius: '20px', fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                                            {a.name}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Section 4: CSV Upload — custom drag-and-drop */}
                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                📎 Participants CSV <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0, marginLeft: '0.25rem', opacity: 0.7 }}>(optional)</span>
                            </label>
                            <div
                                onClick={() => document.getElementById('csv-upload-input').click()}
                                onDrop={(e) => { e.preventDefault(); if (e.dataTransfer.files[0]) setCsvFile(e.dataTransfer.files[0]); }}
                                onDragOver={(e) => e.preventDefault()}
                                style={{ border: `1px dashed ${csvFile ? 'var(--accent-color)' : 'var(--border-color)'}`, borderRadius: '10px', padding: '0.85rem 1rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: csvFile ? 'rgba(139,92,246,0.05)' : 'transparent', transition: 'all 0.2s' }}
                                onMouseOver={e => e.currentTarget.style.borderColor = 'var(--accent-color)'}
                                onMouseOut={e => e.currentTarget.style.borderColor = csvFile ? 'var(--accent-color)' : 'var(--border-color)'}
                            >
                                <span style={{ fontSize: '0.88rem', color: csvFile ? 'var(--accent-color)' : 'var(--text-secondary)' }}>
                                    {csvFile ? `✅ ${csvFile.name}` : 'Drop your CSV here or click to browse — columns: Name, Email'}
                                </span>
                                {csvFile && (
                                    <button type="button" onClick={(e) => { e.stopPropagation(); setCsvFile(null); }}
                                        style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '1.1rem', lineHeight: 1 }}>✕</button>
                                )}
                            </div>
                            <input id="csv-upload-input" type="file" accept=".csv" onChange={(e) => setCsvFile(e.target.files[0])} style={{ display: 'none' }} />
                        </div>

                        {/* Submit */}
                        <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '0.8rem', fontSize: '0.95rem', justifyContent: 'center' }} disabled={botStatus === 'dispatching'}>
                            {botStatus === 'dispatching' ? <RefreshCw className="spin" /> : <Wand2 />}
                            {botStatus === 'dispatching' ? '  Processing...' : (scheduledTime ? '  Schedule Bot' : '  Dispatch Live Bot')}
                        </button>
                    </form>
                    )
                ) : (
                    <div style={{ paddingTop: '2rem' }}>
                        <h3 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>Processing Status</h3>
                        
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '400px', margin: '0 auto' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', opacity: currentStepIndex >= 0 ? 1 : 0.4 }}>
                                {currentStepIndex > 0 ? <CheckCircle2 color="var(--success-color)" /> : currentStepIndex === 0 ? <RefreshCw className="spin" color="var(--accent-color)" /> : <Hourglass />}
                                <span style={{ fontWeight: 500 }}>Pending in Queue</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', opacity: currentStepIndex >= 1 ? 1 : 0.4 }}>
                                {currentStepIndex > 1 ? <CheckCircle2 color="var(--success-color)" /> : currentStepIndex === 1 ? <RefreshCw className="spin" color="var(--accent-color)" /> : <Mic />}
                                <span style={{ fontWeight: 500 }}>Transcribing & Diarizing</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', opacity: currentStepIndex >= 2 ? 1 : 0.4 }}>
                                {currentStepIndex > 2 ? <CheckCircle2 color="var(--success-color)" /> : currentStepIndex === 2 ? <RefreshCw className="spin" color="var(--accent-color)" /> : <Wand2 />}
                                <span style={{ fontWeight: 500 }}>Extracting Action Items</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', opacity: currentStepIndex >= 3 ? 1 : 0.4 }}>
                                {currentStepIndex === 3 ? <CheckCircle2 color="var(--success-color)" /> : <CheckCircle2 />}
                                <span style={{ fontWeight: 500 }}>Complete</span>
                            </div>
                            {status === 'failed' && (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', opacity: 1 }}>
                                    <XCircle color="var(--danger-color)" />
                                    <span style={{ fontWeight: 500, color: 'var(--danger-color)' }}>Processing Failed</span>
                                </div>
                            )}
                        </div>

                        <div style={{ textAlign: 'center', marginTop: '2.5rem' }}>
                            {status === 'done' && (
                                <Link to={`/meetings/${meetingId}/view`} className="btn btn-primary">
                                    View Meeting Details
                                </Link>
                            )}
                            {(status === 'done' || status === 'failed') && (
                                <button className="btn btn-secondary" style={{ marginLeft: '1rem' }} onClick={() => { setStatus('idle'); setBotStatus('idle'); setFile(null); }}>
                                    Process Another
                                </button>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
