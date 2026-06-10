import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import Sidebar from './Sidebar';  // ✅ Fixed: changed from "../Sidebar" to "./Sidebar"

const API = axios.create({ baseURL: '/api' });

API.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function ChatInterface({ user, onLogout }) {
  const [prompt, setPrompt] = useState('');
  const [currentSession, setCurrentSession] = useState(null);
  const [currentTask, setCurrentTask] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [toasts, setToasts] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [tasks, setTasks] = useState([]);
  const pollingRef = useRef(null);

  const addToast = (msg, type = 'error') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, msg, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  };

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const fetchSessions = async () => {
    try {
      const { data } = await API.get('/sessions/');
      setSessions(data);
      if (data.length > 0 && !currentSession) {
        setCurrentSession(data[0]);
      }
    } catch (error) {
      console.error('Failed to fetch sessions');
    }
  };

  const fetchSessionTasks = async (sessionId) => {
    try {
      const { data } = await API.get(`/sessions/${sessionId}/tasks/`);
      setTasks(data);
    } catch (error) {
      console.error('Failed to fetch tasks');
    }
  };

  const cancelTask = async () => {
    if (!currentTaskId) return;
    try {
      await API.post(`/cancel/${currentTaskId}/`);
      addToast('Task cancelled!', 'success');
      stopPolling();
      setIsRunning(false);
      setCurrentTaskId(null);
    } catch (error) {
      addToast('Failed to cancel task');
    }
  };

  const fetchResult = useCallback(async (taskId) => {
    try {
      const { data } = await API.get(`/result/${taskId}/`);
      setCurrentTask(data);
      
      if (data.status === 'done' || data.status === 'error' || data.status === 'cancelled') {
        stopPolling();
        setIsRunning(false);
        if (data.status === 'done') {
          addToast('✅ Task completed!', 'success');
          if (currentSession) fetchSessionTasks(currentSession.session_id);
        } else if (data.status === 'cancelled') {
          addToast('⛔ Task cancelled', 'warning');
        } else {
          addToast(`❌ Error: ${data.error_message}`, 'error');
        }
      }
    } catch (error) {
      addToast('Failed to fetch result');
      stopPolling();
      setIsRunning(false);
    }
  }, [stopPolling, addToast, currentSession]);

  const startPolling = useCallback((taskId) => {
    stopPolling();
    pollingRef.current = setInterval(() => fetchResult(taskId), 2000);
  }, [fetchResult, stopPolling]);

  const runAgents = async () => {
    if (!prompt.trim() || isRunning) return;
    if (prompt.length < 10) {
      addToast('Task too short (min 10 chars)');
      return;
    }
    
    setIsRunning(true);
    setCurrentTask(null);
    
    try {
      const response = await API.post('/run/', { 
        task: prompt,
        session_id: currentSession?.session_id 
      });
      const { task_id } = response.data;
      setCurrentTaskId(task_id);
      startPolling(task_id);
      setPrompt('');
      fetchSessions();
    } catch (err) {
      addToast(err.response?.data?.error || 'Failed to start');
      setIsRunning(false);
    }
  };

  const createNewChat = async () => {
    try {
      const { data } = await API.post('/sessions/', { title: 'New Chat' });
      setSessions([data, ...sessions]);
      setCurrentSession(data);
      setTasks([]);
      setCurrentTask(null);
      addToast('New chat created!', 'success');
    } catch (error) {
      addToast('Failed to create new chat');
    }
  };

  const deleteSession = async (sessionId) => {
    try {
      await API.delete(`/sessions/${sessionId}/`);
      setSessions(sessions.filter(s => s.session_id !== sessionId));
      if (currentSession?.session_id === sessionId) {
        const nextSession = sessions.find(s => s.session_id !== sessionId);
        setCurrentSession(nextSession || null);
        setTasks([]);
      }
      addToast('Chat deleted', 'success');
    } catch (error) {
      addToast('Failed to delete chat');
    }
  };

  const logout = () => {
    onLogout();
  };

  useEffect(() => {
    fetchSessions();
    return () => stopPolling();
  }, []);

  useEffect(() => {
    if (currentSession) {
      fetchSessionTasks(currentSession.session_id);
    }
  }, [currentSession]);

  const steps = [
    { name: 'Planner', key: 'planning', icon: '📋' },
    { name: 'Coder', key: 'coding', icon: '💻' },
    { name: 'Reviewer', key: 'reviewing', icon: '🔍' }
  ];
  
  const getStepStatus = (key) => {
    if (!currentTask) return 'idle';
    if (currentTask.status === 'done') return 'done';
    if (currentTask.status === 'cancelled') return 'cancelled';
    if (currentTask.status === key) return 'active';
    const order = ['planning', 'coding', 'reviewing'];
    if (order.indexOf(currentTask.status) > order.indexOf(key)) return 'done';
    return 'idle';
  };

  return (
    <div className="flex h-screen bg-dark-bg">
      <Sidebar
        sessions={sessions}
        currentSession={currentSession}
        onSelectSession={setCurrentSession}
        onNewChat={createNewChat}
        onDeleteSession={deleteSession}
        onLogout={logout}
      />

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto p-8">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-accent to-purple-500 bg-clip-text text-transparent">
              ⚡ Multi-Agent AI Coder
            </h1>
            <p className="text-gray-400 mt-2">Three AI agents collaborating to write your code</p>
          </div>

          <div className="glass rounded-xl p-6 mb-8">
            <textarea
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              placeholder="Describe what to build..."
              className="w-full h-32 bg-gray-900 border border-gray-700 rounded-lg p-4 text-white"
              disabled={isRunning}
            />

            <div className="flex gap-4 mt-4">
              <button
                onClick={runAgents}
                disabled={isRunning || !prompt.trim()}
                className="px-6 py-3 bg-cyan-accent text-dark-bg font-semibold rounded-lg disabled:opacity-50 flex items-center gap-2"
              >
                {isRunning ? '⏳ Running...' : '⚡ Run Agents'}
              </button>

              {isRunning && (
                <button onClick={cancelTask} className="px-6 py-3 bg-red-600 text-white rounded-lg">
                  🛑 Stop
                </button>
              )}
            </div>
          </div>

          {currentTask && (
            <div className="glass rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">Status: {currentTask.status}</h2>
              {currentTask.plan && (
                <div className="mb-4">
                  <h3 className="font-semibold text-cyan-accent">📋 Plan</h3>
                  <pre className="bg-gray-900 p-4 rounded mt-2 text-sm">{currentTask.plan}</pre>
                </div>
              )}
              {currentTask.code && (
                <div className="mb-4">
                  <h3 className="font-semibold text-cyan-accent">💻 Code</h3>
                  <pre className="bg-gray-900 p-4 rounded mt-2 text-sm">{currentTask.code}</pre>
                </div>
              )}
              {currentTask.final_code && (
                <div>
                  <h3 className="font-semibold text-green-500">✅ Final Code</h3>
                  <pre className="bg-gray-900 p-4 rounded mt-2 text-sm">{currentTask.final_code}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {toasts.map(t => (
        <div key={t.id} className={`fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50
          ${t.type === 'success' ? 'bg-green-500' : t.type === 'warning' ? 'bg-yellow-500' : 'bg-red-500'} text-white`}>
          {t.msg}
        </div>
      ))}
    </div>
  );
}

export default ChatInterface;