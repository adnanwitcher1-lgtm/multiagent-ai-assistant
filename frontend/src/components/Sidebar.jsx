import React from 'react';

function Sidebar({ sessions, currentSession, onSelectSession, onNewChat, onDeleteSession, onLogout }) {
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  return (
    <div className="w-80 glass border-r border-gray-800 flex flex-col">
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">💬 Chats</h2>
          <button 
            onClick={onNewChat} 
            className="px-3 py-1 bg-cyan-accent text-dark-bg rounded-lg text-sm hover:bg-cyan-300 transition-all"
          >
            + New Chat
          </button>
        </div>
        <div className="text-sm text-gray-400">
          Logged in as: <span className="text-cyan-accent">{user.username || 'User'}</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>No chats yet</p>
            <p className="text-xs mt-2">Click "New Chat" to start</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {sessions.map((session) => (
              <div
                key={session.session_id}
                className={`group hover:bg-gray-800/50 transition-all cursor-pointer
                  ${currentSession?.session_id === session.session_id ? 'bg-gray-800/70 border-l-4 border-cyan-accent' : ''}`}
              >
                <div
                  onClick={() => onSelectSession(session)}
                  className="p-4"
                >
                  <p className="text-sm font-medium text-gray-200 truncate">
                    {session.title}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(session.updated_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm('Delete this chat?')) {
                      onDeleteSession(session.session_id);
                    }
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition-all"
                >
                  🗑️
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="p-4 border-t border-gray-800">
        <button
          onClick={onLogout}
          className="w-full px-4 py-2 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30 transition-all flex items-center justify-center gap-2"
        >
          <span>🚪</span> Logout
        </button>
      </div>
    </div>
  );
}

export default Sidebar;