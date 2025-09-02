import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import AuthGoogle from './components/AuthGoogle';
import Callback from './components/Callback';
import GraphView from './components/GraphView';
import HealthCheck from './components/HealthCheck';
import './index.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8001';

// Dashboard component with futuristic design
const Dashboard = ({ user }) => {
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [storyContent, setStoryContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  return (
    <div className="min-h-screen bg-cyber-black cyber-grid">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Panel - Story Editor */}
          <div className="lg:col-span-2 space-y-6">
            <div className="glass-strong rounded-2xl p-8 shadow-cyber liquid-morph">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold cyber-heading">
                  AI Story Co-Creation Studio
                </h2>
                <div className="flex items-center space-x-3">
                  <button className="cyber-button px-4 py-2 rounded-lg font-medium transition-all duration-300">
                    <svg className="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    Suggest
                  </button>
                  <button className="cyber-button px-4 py-2 rounded-lg font-medium transition-all duration-300">
                    <svg className="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    Save
                  </button>
                </div>
              </div>
              
              {/* Story Editor */}
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-neon-orange-500/5 to-transparent rounded-xl"></div>
                <textarea
                  value={storyContent}
                  onChange={(e) => setStoryContent(e.target.value)}
                  onFocus={() => setIsEditing(true)}
                  onBlur={() => setIsEditing(false)}
                  placeholder="Start writing your story here... The AI will help you create something amazing."
                  className={`relative z-10 w-full h-96 cyber-input rounded-xl p-6 text-lg leading-relaxed resize-none transition-all duration-300 ${
                    isEditing ? 'neon-glow' : ''
                  }`}
                />
                
                {/* Writing Stats */}
                <div className="flex justify-between items-center mt-4 text-sm text-cyber-gray-300">
                  <div className="flex space-x-6">
                    <span>Words: <span className="neon-text font-semibold">{storyContent.split(' ').filter(word => word.length > 0).length}</span></span>
                    <span>Characters: <span className="neon-text font-semibold">{storyContent.length}</span></span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-neon-orange-500 rounded-full animate-pulse"></div>
                    <span className="cyber-subheading">Ready</span>
                  </div>
                </div>
              </div>
            </div>
            
            {/* AI Suggestions Panel */}
            <div className="glass-strong rounded-2xl p-6 shadow-cyber">
              <h3 className="text-lg font-semibold cyber-heading mb-6 flex items-center">
                <svg className="w-6 h-6 mr-3 animate-pulse" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
                AI Creative Suggestions
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="glass rounded-xl p-4 border-cyber hover:neon-glow-strong transition-all duration-300 group">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-medium cyber-subheading">Option {i}</span>
                      <span className="text-xs px-2 py-1 bg-neon-orange-500/20 text-neon-orange-300 rounded-full">
                        95% coherence
                      </span>
                    </div>
                    <p className="text-white text-sm mb-4 leading-relaxed">
                      Sample continuation text that shows how the story might continue with enhanced narrative flow...
                    </p>
                    <div className="flex space-x-2">
                      <button className="cyber-button px-3 py-1 text-xs rounded hover:scale-105 transform transition-all duration-200 bg-green-600/20 hover:bg-green-600/40 border-green-500/30">
                        Accept
                      </button>
                      <button className="cyber-button px-3 py-1 text-xs rounded hover:scale-105 transform transition-all duration-200">
                        Edit
                      </button>
                      <button className="cyber-button px-3 py-1 text-xs rounded hover:scale-105 transform transition-all duration-200 bg-red-600/20 hover:bg-red-600/40 border-red-500/30">
                        Reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          
          {/* Right Panel - Knowledge Graph & Session Info */}
          <div className="space-y-6">
            {/* Knowledge Graph */}
            <div className="glass-strong rounded-2xl overflow-hidden shadow-cyber">
              <GraphView sessionId={currentSessionId} />
            </div>
            
            {/* Character & Fact Check Panel */}
            <div className="glass-strong rounded-2xl p-6 shadow-cyber liquid-morph-alt">
              <h3 className="text-lg font-semibold cyber-heading mb-4 flex items-center">
                <div className="w-3 h-3 bg-neon-orange-500 rounded-full mr-3 animate-glow"></div>
                Story Analytics
              </h3>
              <div className="space-y-4">
                <div className="p-4 glass rounded-xl">
                  <h4 className="text-sm font-medium cyber-subheading mb-2">Fact Check Status</h4>
                  <div className="flex items-center text-sm">
                    <svg className="w-4 h-4 mr-2 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span className="text-green-400 font-semibold">All facts verified</span>
                  </div>
                </div>
                <div className="p-4 glass rounded-xl">
                  <h4 className="text-sm font-medium cyber-subheading mb-2">Character Profiles</h4>
                  <div className="space-y-2 text-sm text-white">
                    <div className="flex items-center">
                      <div className="w-2 h-2 bg-neon-orange-500 rounded-full mr-2 animate-pulse"></div>
                      Main Character: Consistent portrayal
                    </div>
                    <div className="flex items-center">
                      <div className="w-2 h-2 bg-blue-400 rounded-full mr-2 animate-pulse"></div>
                      Supporting Characters: 2 active
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Session Control Panel */}
            <div className="glass-strong rounded-2xl p-6 shadow-cyber">
              <h3 className="text-lg font-semibold cyber-heading mb-4 flex items-center">
                <svg className="w-5 h-5 mr-3 animate-spin text-neon-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Session Control
              </h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="p-3 glass rounded-lg border-cyber">
                    <div className="cyber-subheading text-xs mb-1">Mode</div>
                    <div className="text-white font-semibold">Balanced</div>
                  </div>
                  <div className="p-3 glass rounded-lg border-cyber">
                    <div className="cyber-subheading text-xs mb-1">Topic</div>
                    <div className="text-white font-semibold">Story</div>
                  </div>
                  <div className="p-3 glass rounded-lg border-cyber">
                    <div className="cyber-subheading text-xs mb-1">Word Count</div>
                    <div className="text-white font-semibold">{storyContent.split(' ').filter(word => word.length > 0).length}</div>
                  </div>
                  <div className="p-3 glass rounded-lg border-cyber">
                    <div className="cyber-subheading text-xs mb-1">Status</div>
                    <div className="text-neon-orange-400 font-semibold flex items-center">
                      <div className="w-2 h-2 bg-neon-orange-500 rounded-full mr-1 animate-pulse"></div>
                      Active
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* System Health */}
            <div className="glass-strong rounded-2xl overflow-hidden shadow-cyber">
              <HealthCheck />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Protected Route component
const ProtectedRoute = ({ children, user }) => {
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check authentication status on app load
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Check localStorage first
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          setUser(JSON.parse(storedUser));
        }

        // Verify with backend
        const response = await fetch(`${API_BASE_URL}/api/me`, {
          credentials: 'include',
        });

        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
          localStorage.setItem('user', JSON.stringify(userData));
        } else {
          // Clear invalid stored data
          localStorage.removeItem('user');
          setUser(null);
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('user');
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const handleSignOut = async () => {
    try {
      await fetch('/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.error('Sign out error:', error);
    } finally {
      localStorage.removeItem('user');
      setUser(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <Router>
      <div className="App">
        {user && <Navbar user={user} onSignOut={handleSignOut} />}
        
        <Routes>
          <Route 
            path="/login" 
            element={user ? <Navigate to="/" replace /> : <AuthGoogle />} 
          />
          <Route 
            path="/auth/callback" 
            element={<Callback />} 
          />
          <Route 
            path="/" 
            element={
              <ProtectedRoute user={user}>
                <Dashboard user={user} />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="*" 
            element={<Navigate to={user ? "/" : "/login"} replace />} 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
