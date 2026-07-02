import React, { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { UploadCloud, Hourglass, Mic, Wand2, CheckCircle2, RefreshCw, XCircle } from 'lucide-react';

export default function Upload() {
    const [file, setFile] = useState(null);
    const [status, setStatus] = useState('idle'); // idle, uploading, pending, transcribing, extracting, done, failed
    const [meetingId, setMeetingId] = useState(null);
    const fileInputRef = useRef(null);

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

    const steps = ['pending', 'transcribing', 'extracting', 'done'];
    const currentStepIndex = steps.indexOf(status);

    const isProcessing = ['pending', 'transcribing', 'extracting', 'uploading'].includes(status);

    return (
        <div className="animate-fade-in delay-1" style={{ maxWidth: '800px', margin: '0 auto' }}>
            <h1>Upload Meeting</h1>
            <p>Upload an audio or video recording to begin processing.</p>

            <div className="glass-panel" style={{ marginTop: '2rem' }}>
                {status === 'idle' || status === 'uploading' ? (
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
                                <button className="btn btn-secondary" style={{ marginLeft: '1rem' }} onClick={() => { setStatus('idle'); setFile(null); }}>
                                    Upload Another
                                </button>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
