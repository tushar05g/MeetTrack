import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { Check } from 'lucide-react';

export default function Tasks() {
    const [tasks, setTasks] = useState([]);
    const [loading, setLoading] = useState(true);

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

    if (loading) return <div style={{textAlign: 'center', marginTop: '5rem'}}>Loading...</div>;

    return (
        <div className="animate-fade-in delay-1">
            <h1>All Tasks</h1>
            <p>Manage all action items extracted across your meetings.</p>

            <div className="glass-panel table-container" style={{ marginTop: '2rem' }}>
                <table className="table">
                    <thead>
                        <tr>
                            <th>Task Description</th>
                            <th>Meeting ID</th>
                            <th>Owner</th>
                            <th>Deadline</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tasks.length === 0 ? (
                            <tr>
                                <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                                    No tasks found.
                                </td>
                            </tr>
                        ) : tasks.map(task => (
                            <tr key={task.id}>
                                <td style={{ fontWeight: 500 }}>{task.description}</td>
                                <td><Link to={`/meetings/${task.meeting_id}/view`}>#{task.meeting_id}</Link></td>
                                <td>{task.owner || 'Unassigned'}</td>
                                <td style={{ color: task.deadline ? 'var(--warning-color)' : 'inherit' }}>
                                    {task.deadline || '-'}
                                </td>
                                <td>
                                    <span className={`badge badge-${task.status}`}>
                                        {task.status}
                                    </span>
                                </td>
                                <td>
                                    {task.status !== 'done' ? (
                                        <button 
                                            className="btn btn-secondary" 
                                            style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }} 
                                            onClick={() => markDone(task.id)}
                                        >
                                            <Check size={14} /> Done
                                        </button>
                                    ) : (
                                        '-'
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
