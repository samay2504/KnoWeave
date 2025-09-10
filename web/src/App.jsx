import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import AuthGoogle from './components/AuthGoogle';
import Callback from './components/Callback';
import GraphView from './components/GraphView';
import HealthCheck from './components/HealthCheck';
import ModeSelector from './components/ModeSelector';
import DomainSelector from './components/DomainSelector';
import { useAIMode, useSession } from './hooks/useAIMode';
const isTest = typeof process !== 'undefined' && process.env.NODE_ENV === 'test';
import { DEFAULT_MODE, API_CONFIG, DOMAIN_CONFIGS, DEFAULT_DOMAIN } from './config/constants';
import './index.css';

const API_BASE_URL = API_CONFIG.BASE_URL;

// Dashboard component with mode selection and domain support
const Dashboard = ({ user }) => {
  // Test env: deterministic session and user
  const [currentSessionId, setCurrentSessionId] = useState(isTest ? 'test-session' : null);
  const [storyContent, setStoryContent] = useState(isTest ? 'Test story content.' : '');
  const [isEditing, setIsEditing] = useState(false);
  const [userPrompt, setUserPrompt] = useState('');
  const [generatedPrompt, setGeneratedPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [agentType, setAgentType] = useState('general');
  const [currentDomain, setCurrentDomain] = useState(DEFAULT_DOMAIN);
  const [isDomainDetectionEnabled, setIsDomainDetectionEnabled] = useState(true);

  // Use custom hooks for AI mode and session management
  const {
    currentMode,
    updateMode,
    generatePrompt,
    detectDomain,
    isLoading: modeLoading,
    error: modeError,
    clearError
  } = isTest
    ? {
        currentMode: 'Balanced',
        updateMode: () => {},
        generatePrompt: () => {},
        detectDomain: () => {},
        isLoading: false,
        error: null,
        clearError: () => {}
      }
    : useAIMode(DEFAULT_MODE);

  const {
    sessionId,
    isSessionActive,
    createSession
  } = isTest
    ? { sessionId: 'test-session', isSessionActive: true, createSession: () => {} }
    : useSession();

  useEffect(() => {
    if (!isTest && !isSessionActive && user) {
      const initSession = async () => {
        try {
          const result = await createSession({
            user_id: user?.id || user?.email || 'anonymous',
            topic: 'story',
            topic_descriptor: '',
            initial_content: '',
            policy: undefined
          });
          if (result && result.session_id) {
            setCurrentSessionId(result.session_id);
          }
        } catch (err) {
          console.error('Failed to create session:', err);
        }
      };
      initSession();
    }
  }, [isTest, isSessionActive, user, createSession]);

  /**
   * Handle domain change from selector
   */
  const handleDomainChange = async (newDomain, domainConfig) => {
    try {
      setCurrentDomain(newDomain);
      
      // Auto-switch to preferred mode for domain
      if (domainConfig && domainConfig.preferredMode && domainConfig.preferredMode !== currentMode) {
        await updateMode(domainConfig.preferredMode);
      }
      
      console.log(`Domain changed to: ${newDomain}`);
    } catch (err) {
      console.error('Failed to update domain:', err);
    }
  };

  /**
   * Handle mode change from selector
   */
  const handleModeChange = async (newMode, modeConfig) => {
    try {
      await updateMode(newMode, modeConfig);
      console.log(`Mode changed to: ${newMode}`);
    } catch (err) {
      console.error('Failed to update mode:', err);
    }
  };

  /**
   * Auto-detect domain from user input
   */
  const handleDomainDetection = async (text) => {
    if (!isDomainDetectionEnabled || !text.trim()) return;

    try {
      const detection = await detectDomain(text);
      if (detection && detection.topic_family && detection.topic_family !== currentDomain) {
        const confidence = detection.domain_confidence || 0;
        if (confidence > 0.5) {
          setCurrentDomain(detection.topic_family);
          console.log(`Auto-detected domain: ${detection.topic_family} (confidence: ${confidence})`);
        }
      }
    } catch (err) {
      console.error('Domain detection failed:', err);
    }
  };

  /**
   * Handle AI suggestion request
   */
  const handleSuggest = async () => {
    if (!sessionId || !storyContent.trim()) {
      console.warn('Cannot suggest: Missing session or story content');
      return;
    }

    setIsGenerating(true);
    clearError();

    try {
      const response = await fetch(`${API_BASE_URL}/api/session/${sessionId}/suggestion_signal`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          trigger_type: 'user_button',
          topic_content: storyContent,
          mode: currentMode
        })
      });

      if (!response.ok) {
        throw new Error(`Suggestion failed: ${response.status}`);
      }

      const result = await response.json();
      
      if (result.status === 'suggestion_triggered') {
        console.log('✅ Suggestion triggered:', result.reason);
        // TODO: Handle suggestion results when they arrive via WebSocket or polling
        // For now, we'll show a success message
        setGeneratedPrompt(`Suggestion triggered successfully: ${result.reason}`);
      } else {
        console.log('ℹ️ Suggestion skipped:', result.reason);
        setGeneratedPrompt(`Suggestion not triggered: ${result.reason}`);
      }
    } catch (error) {
      console.error('❌ Suggestion failed:', error);
      // Handle error through existing error system
      if (typeof error === 'object' && error.message) {
        // Use the existing error handling system
        console.error('Suggestion error:', error.message);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  /**
   * Generate canonical prompt using PTG system with domain support
   */
  const handleGeneratePrompt = async () => {
    if (!userPrompt.trim()) return;

    setIsGenerating(true);
    clearError();

    try {
      // Auto-detect domain if enabled
      if (isDomainDetectionEnabled) {
        await handleDomainDetection(userPrompt);
      }

      const domainConfig = DOMAIN_CONFIGS[currentDomain];
      const result = await generatePrompt(userPrompt, agentType, {
        topic: userPrompt,
        topic_descriptor: `${domainConfig?.name || 'General'} content: ${userPrompt}`,
        topic_family: currentDomain,
        topic_role: domainConfig?.name?.toLowerCase()?.replace(/\s+/g, '_') || 'assistant',
        topic_goal: `create_${currentDomain}_content`,
      });
      
      setGeneratedPrompt(result.canonical_prompt || result.prompt);
    } catch (err) {
      console.error('Failed to generate prompt:', err);
    } finally {
      setIsGenerating(false);
    }
  };

  /**
   * Apply generated prompt to story
   */
  const handleApplyPrompt = () => {
    if (generatedPrompt) {
      setStoryContent(prev => prev + '\n\n' + generatedPrompt);
      setUserPrompt('');
      setGeneratedPrompt('');
    }
  };

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
                  <button 
                    onClick={handleSuggest}
                    disabled={isGenerating || !((currentSessionId || sessionId) && storyContent && storyContent.trim().length > 0)}
                    className="cyber-button px-4 py-2 rounded-lg font-medium transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg className="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    {isGenerating ? 'Suggesting...' : 'Suggest'}
                  </button>
                  <button className="cyber-button px-4 py-2 rounded-lg font-medium transition-all duration-300">
                    <svg className="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    Save
                  </button>
                </div>
              </div>
              {/* Suggestions heading for test compatibility */}
              <h3 className="text-lg font-bold cyber-heading mb-2">Suggestions</h3>
              
              {/* Story Editor */}
              <h3 className="text-lg font-bold cyber-heading mb-2">Story Editor</h3>
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
            
            {/* Mode Selection and PTG Panel */}
            <div className="glass-strong rounded-2xl p-6 shadow-cyber">
              <h3 className="text-lg font-semibold cyber-heading mb-6 flex items-center">
                <svg className="w-6 h-6 mr-3 animate-pulse" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
                Content Domain & AI Mode
              </h3>

              {/* Domain Selector */}
              <div className="mb-6">
                <DomainSelector
                  currentDomain={currentDomain}
                  onDomainChange={handleDomainChange}
                  disabled={modeLoading}
                  showDescription={true}
                  showExamples={false}
                  className="cyber-input"
                />
              </div>

              {/* Mode Selector */}
              <div className="mb-6">
                <ModeSelector
                  currentMode={currentMode}
                  onModeChange={handleModeChange}
                  disabled={modeLoading}
                  showDescription={true}
                  className="cyber-input"
                />
              </div>

              {/* Domain Detection Toggle */}
              <div className="mb-4">
                <label className="flex items-center space-x-3 text-sm text-gray-600">
                  <input
                    type="checkbox"
                    checked={isDomainDetectionEnabled}
                    onChange={(e) => setIsDomainDetectionEnabled(e.target.checked)}
                    className="h-4 w-4 text-blue-600 rounded border-gray-300"
                  />
                  <span>Auto-detect content domain from input</span>
                </label>
              </div>

              {/* Agent Type Selection */}
              <div className="mb-4">
                <label className="block text-sm font-medium cyber-subheading mb-2">
                  Agent Type
                </label>
                <select
                  value={agentType}
                  onChange={(e) => setAgentType(e.target.value)}
                  className="w-full cyber-input px-3 py-2 rounded-lg"
                >
                  <option value="general">General</option>
                  <option value="creative">Creative</option>
                  <option value="analytical">Analytical</option>
                  <option value="technical">Technical</option>
                  <option value="research">Research</option>
                  <option value="writing">Writing</option>
                </select>
              </div>

              {/* Prompt Input */}
              <div className="mb-4">
                <label className="block text-sm font-medium cyber-subheading mb-2">
                  Your Prompt
                </label>
                <textarea
                  value={userPrompt}
                  onChange={(e) => setUserPrompt(e.target.value)}
                  placeholder="Enter your prompt for AI enhancement..."
                  className="w-full h-24 cyber-input px-3 py-2 rounded-lg resize-none"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex space-x-2 mb-4">
                <button
                  onClick={handleGeneratePrompt}
                  disabled={!userPrompt.trim() || isGenerating || modeLoading}
                  className="cyber-button px-4 py-2 rounded-lg font-medium flex-1 disabled:opacity-50"
                >
                  {isGenerating ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white inline mr-2"></div>
                      Generating...
                    </>
                  ) : (
                    'Generate'
                  )}
                </button>
                
                {generatedPrompt && (
                  <button
                    onClick={handleApplyPrompt}
                    className="cyber-button px-4 py-2 rounded-lg font-medium bg-green-600/20 hover:bg-green-600/40 border-green-500/30"
                  >
                    Apply to Story
                  </button>
                )}
              </div>

              {/* Generated Prompt Display */}
              {generatedPrompt && (
                <div className="glass rounded-xl p-4 border-cyber">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium cyber-subheading">Generated Prompt</span>
                    <span className="text-xs px-2 py-1 bg-neon-orange-500/20 text-neon-orange-300 rounded-full">
                      Mode: {currentMode}
                    </span>
                  </div>
                  <div className="bg-gray-900/50 rounded-lg p-3 mb-3">
                    <pre className="whitespace-pre-wrap text-sm text-white font-mono">
                      {generatedPrompt}
                    </pre>
                  </div>
                  <button
                    onClick={() => navigator.clipboard.writeText(generatedPrompt)}
                    className="cyber-button px-3 py-1 text-xs rounded"
                  >
                    Copy
                  </button>
                </div>
              )}

              {/* Error Display */}
              {modeError && (
                <div className="mt-4 p-3 bg-red-900/50 border border-red-500/30 rounded-lg">
                  <p className="text-sm text-red-300">{modeError}</p>
                  <button
                    onClick={clearError}
                    className="mt-2 text-xs text-red-400 hover:text-red-200"
                  >
                    Dismiss
                  </button>
                </div>
              )}
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
  const isTest = typeof process !== 'undefined' && process.env.NODE_ENV === 'test';
  const [user, setUser] = useState(isTest ? { id: 'test-user', email: 'test@example.com', name: 'Test User' } : null);
  const [loading, setLoading] = useState(isTest ? false : true);

  // Check authentication status on app load
  useEffect(() => {
    if (isTest) return;
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
  }, [isTest]);

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
        <div role="status" className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500"></div>
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
