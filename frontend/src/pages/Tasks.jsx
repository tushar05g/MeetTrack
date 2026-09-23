import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { 
    Check, 
    ListTodo, 
    Search, 
    Filter, 
    Calendar, 
    User, 
    ExternalLink, 
    CheckCircle2, 
    Clock, 
    Sparkles,
    RefreshCw
} from 'lucide-react';

export default function Tasks() {
    const [tasks, setTasks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState('all'); // all, pending, done

    useEffect(() => {
        fetchTasks();
    }, []);

    const fetchTasks = async () => {
        try {
            const res = await api.get('/tasks');
            setTasks(res.data);
            setLoading(false);
        } catch (err) {
            console.error("Error fetching tasks", err);
            setLoading(false);
        }
    };

    const markDone = async (taskId) => {
        try {
            await api.patch(`/tasks/${taskId}`, { status: 'done' });
            setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: 'done' } : t));
        } catch (err) {
            alert('Error updating task: ' + err.message);
        }
    };

    // Filter tasks based on search and status
    const filteredTasks = useMemo(() => {
        return tasks.filter(task => {
            const matchesStatus = statusFilter === 'all' 
                ? true 
                : statusFilter === 'done' 
                ? task.status === 'done' 
                : task.status !== 'done';
            
            const matchesSearch = !searchQuery || 
                (task.description && task.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
                (task.owner && task.owner.toLowerCase().includes(searchQuery.toLowerCase())) ||
                (task.meeting_id && task.meeting_id.toString().includes(searchQuery));

            return matchesStatus && matchesSearch;
        });
    }, [tasks, statusFilter, searchQuery]);

    const completedCount = tasks.filter(t => t.status === 'done').length;
    const pendingCount = tasks.length - completedCount;
    const progressPercent = tasks.length > 0 ? Math.round((completedCount / tasks.length) * 100) : 0;

    if (loading) {
        return (
            <div style={{ textAlign: 'center', marginTop: '6rem', color: 'var(--text-secondary)' }}>
                <RefreshCw size={36} className="spin" style={{ color: 'var(--accent-hover)', marginBottom: '1rem' }} />
                <p style={{ fontSize: '1rem' }}>Loading action items...</p>
            </div>
        );
    }

    return (
        <div className="animate-fade-in delay-1" style={{ paddingBottom: '3rem' }}>
            {/* Header Section */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1.5rem', marginBottom: '2rem' }}>
                <div>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem', padding: '0.3rem 0.75rem', borderRadius: '999px', background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.25)', color: 'var(--accent-hover)', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.6rem' }}>
                        <Sparkles size={13} /> Action Intelligence
                    </div>
                    <h1 style={{ fontSize: '2rem', fontWeight: 800, letterSpacing: '-0.02em', margin: '0 0 0.4rem 0' }}>
                        Tasks & Action Items
                    </h1>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', margin: 0 }}>
                        Cross-meeting deliverables extracted and assigned by AI models.
                    </p>
                </div>

                {/* Progress Widget */}
                {tasks.length > 0 && (
                    <div className="glass-panel" style={{ padding: '1rem 1.4rem', borderRadius: '14px', border: '1px solid var(--border-color)', minWidth: '240px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', fontSize: '0.82rem' }}>
                            <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Overall Progress</span>
                            <span style={{ fontWeight: 700, color: 'var(--accent-hover)' }}>{progressPercent}%</span>
                        </div>
                        <div style={{ width: '100%', height: '8px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '999px', overflow: 'hidden' }}>
                            <div 
                                style={{ 
                                    width: `${progressPercent}%`, 
                                    height: '100%', 
                                    background: 'linear-gradient(90deg, #6366f1, #10b981)', 
                                    borderRadius: '999px',
                                    transition: 'width 0.4s ease'
                                }} 
                            />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                            <span>{completedCount} Done</span>
                            <span>{pendingCount} Pending</span>
                        </div>
                    </div>
                )}
            </div>

            {/* Filter and Search Bar */}
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                {/* Search Bar */}
                <div style={{ position: 'relative', flex: '1 1 280px', maxWidth: '420px' }}>
                    <Search size={16} style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                    <input 
                        type="text"
                        placeholder="Search tasks by description, owner, or meeting..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        style={{
                            width: '100%',
                            padding: '0.65rem 0.85rem 0.65rem 2.4rem',
                            borderRadius: '10px',
                            border: '1px solid var(--border-color)',
                            background: 'var(--bg-secondary)',
                            color: 'var(--text-primary)',
                            fontSize: '0.88rem',
                            outline: 'none',
                            boxSizing: 'border-box'
                        }}
                    />
                </div>

                {/* Status Filter Pills */}
                <div style={{ display: 'flex', gap: '0.4rem', background: 'rgba(15, 23, 42, 0.5)', padding: '0.3rem', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
                    {[
                        { id: 'all', label: 'All Tasks', count: tasks.length },
                        { id: 'pending', label: 'Pending', count: pendingCount },
                        { id: 'done', label: 'Completed', count: completedCount }
                    ].map(f => {
                        const isActive = statusFilter === f.id;
                        return (
                            <button
                                key={f.id}
                                onClick={() => setStatusFilter(f.id)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.4rem',
                                    padding: '0.45rem 0.85rem',
                                    borderRadius: '8px',
                                    border: 'none',
                                    fontSize: '0.82rem',
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    transition: 'all 0.2s ease',
                                    background: isActive ? 'linear-gradient(135deg, #6366f1, #4f46e5)' : 'transparent',
                                    color: isActive ? '#ffffff' : 'var(--text-secondary)'
                                }}
                            >
                                {f.label}
                                <span style={{
                                    fontSize: '0.72rem',
                                    padding: '0.1rem 0.4rem',
                                    borderRadius: '999px',
                                    background: isActive ? 'rgba(255, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                                    color: isActive ? '#ffffff' : 'var(--text-secondary)'
                                }}>
                                    {f.count}
                                </span>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Tasks Table Panel */}
            <div className="glass-panel table-container" style={{ borderRadius: '16px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
                <table className="table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr style={{ background: 'rgba(15, 23, 42, 0.6)' }}>
                            <th style={{ width: '42%', padding: '1rem 1.25rem' }}>Task Description</th>
                            <th style={{ width: '14%', padding: '1rem' }}>Meeting</th>
                            <th style={{ width: '16%', padding: '1rem' }}>Assignee</th>
                            <th style={{ width: '14%', padding: '1rem' }}>Deadline</th>
                            <th style={{ width: '14%', padding: '1rem 1.25rem', textAlign: 'right' }}>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredTasks.length === 0 ? (
                            <tr>
                                <td colSpan="5" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '4rem 1rem' }}>
                                    <ListTodo size={40} style={{ opacity: 0.3, marginBottom: '0.75rem', margin: '0 auto', display: 'block' }} />
                                    <p style={{ margin: '0 0 0.5rem 0', fontWeight: 600, color: 'var(--text-primary)' }}>No tasks found</p>
                                    <p style={{ margin: 0, fontSize: '0.85rem' }}>
                                        {searchQuery || statusFilter !== 'all' 
                                            ? 'Try modifying your search or filter filters.' 
                                            : 'Action items will appear here once processed from your meetings.'}
                                    </p>
                                </td>
                            </tr>
                        ) : (
                            filteredTasks.map(task => {
                                const isDone = task.status === 'done';
                                return (
                                    <tr 
                                        key={task.id}
                                        style={{ 
                                            borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                                            background: isDone ? 'rgba(16, 185, 129, 0.02)' : 'transparent',
                                            transition: 'background 0.2s ease'
                                        }}
                                    >
                                        <td style={{ padding: '1rem 1.25rem', verticalAlign: 'middle' }}>
                                            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                                                {isDone ? (
                                                    <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.15)', color: 'var(--success-color)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: '2px', flexShrink: 0 }}>
                                                        <Check size={12} strokeWidth={3} />
                                                    </div>
                                                ) : (
                                                    <button
                                                        onClick={() => markDone(task.id)}
                                                        title="Mark task done"
                                                        style={{
                                                            width: '20px',
                                                            height: '20px',
                                                            borderRadius: '50%',
                                                            border: '2px solid rgba(255, 255, 255, 0.2)',
                                                            background: 'transparent',
                                                            cursor: 'pointer',
                                                            marginTop: '2px',
                                                            flexShrink: 0,
                                                            transition: 'all 0.2s'
                                                        }}
                                                        onMouseOver={e => e.currentTarget.style.borderColor = 'var(--accent-hover)'}
                                                        onMouseOut={e => e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)'}
                                                    />
                                                )}
                                                <span style={{ 
                                                    fontWeight: 500, 
                                                    fontSize: '0.92rem', 
                                                    color: isDone ? 'var(--text-secondary)' : 'var(--text-primary)',
                                                    textDecoration: isDone ? 'line-through' : 'none',
                                                    lineHeight: 1.45
                                                }}>
                                                    {task.description}
                                                </span>
                                            </div>
                                        </td>
                                        
                                        <td style={{ padding: '1rem', verticalAlign: 'middle' }}>
                                            <Link 
                                                to={`/meetings/${task.meeting_id}/view`}
                                                style={{ 
                                                    display: 'inline-flex', 
                                                    alignItems: 'center', 
                                                    gap: '0.35rem', 
                                                    fontSize: '0.85rem',
                                                    color: 'var(--accent-hover)',
                                                    fontWeight: 600,
                                                    background: 'rgba(99, 102, 241, 0.1)',
                                                    padding: '0.25rem 0.55rem',
                                                    borderRadius: '6px',
                                                    border: '1px solid rgba(99, 102, 241, 0.2)'
                                                }}
                                            >
                                                #{task.meeting_id} <ExternalLink size={11} />
                                            </Link>
                                        </td>

                                        <td style={{ padding: '1rem', verticalAlign: 'middle' }}>
                                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                                <User size={13} style={{ color: 'var(--accent-hover)' }} />
                                                <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                                                    {task.owner || 'Unassigned'}
                                                </span>
                                            </span>
                                        </td>

                                        <td style={{ padding: '1rem', verticalAlign: 'middle' }}>
                                            {task.deadline ? (
                                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.82rem', color: 'var(--warning-color)' }}>
                                                    <Calendar size={13} /> {task.deadline}
                                                </span>
                                            ) : (
                                                <span style={{ color: 'var(--text-secondary)', opacity: 0.5, fontSize: '0.85rem' }}>-</span>
                                            )}
                                        </td>

                                        <td style={{ padding: '1rem 1.25rem', textAlign: 'right', verticalAlign: 'middle' }}>
                                            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <span className={`badge badge-${task.status}`} style={{ fontSize: '0.72rem', textTransform: 'capitalize' }}>
                                                    {task.status}
                                                </span>
                                                {!isDone && (
                                                    <button 
                                                        className="btn btn-secondary" 
                                                        style={{ padding: '0.3rem 0.6rem', fontSize: '0.78rem', borderRadius: '6px' }} 
                                                        onClick={() => markDone(task.id)}
                                                    >
                                                        <Check size={13} /> Done
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
