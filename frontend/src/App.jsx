import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Signup from './components/Signup';
import Login from './components/Login';
import ChatInterface from './components/ChatInterface';

// Configure axios base URL
axios.defaults.baseURL = import.meta.env.VITE_API_URL || '';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [showSignup, setShowSignup] = useState(true);
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('access_token');
    const savedUser = localStorage.getItem('user');
    if (token && savedUser) {
      setIsAuthenticated(true);
      setUser(JSON.parse(savedUser));
      // Set default authorization header
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
    setUser(null);
    setShowSignup(true);
    delete axios.defaults.headers.common['Authorization'];
  };

  if (!isAuthenticated) {
    return showSignup ? (
      <Signup
        setShowSignup={setShowSignup}
        setIsAuthenticated={setIsAuthenticated}
        setUser={setUser}
      />
    ) : (
      <Login
        setShowSignup={setShowSignup}
        setIsAuthenticated={setIsAuthenticated}
        setUser={setUser}
      />
    );
  }

  return (
    <div className="min-h-screen bg-dark-bg">
      <ChatInterface user={user} onLogout={handleLogout} />
    </div>
  );
}

export default App;
