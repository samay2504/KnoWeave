import React, { useState, useEffect, useRef } from 'react';

const Navbar = ({ user, onSignOut, currentSession, sessionList = [], onSessionChange }) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isSessionDropdownOpen, setIsSessionDropdownOpen] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const dropdownRef = useRef(null);
  const sessionDropdownRef = useRef(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
      if (sessionDropdownRef.current && !sessionDropdownRef.current.contains(event.target)) {
        setIsSessionDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Close mobile menu on escape key
  useEffect(() => {
    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setIsMenuOpen(false);
        setIsDropdownOpen(false);
        setIsSessionDropdownOpen(false);
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, []);

  const formatSessionName = (session) => {
    if (!session) return 'No Session';
    return session.name || session.session_id || 'Unnamed Session';
  };

  const formatSessionTime = (session) => {
    if (!session?.created_at) return '';
    try {
      return new Date(session.created_at).toLocaleString();
    } catch {
      return '';
    }
  };

  return (
    <nav className="backdrop-cyber border-b border-neon-orange-500/20 sticky top-0 z-50 shadow-cyber">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo and Branding */}
          <div className="flex items-center">
            <div className="flex-shrink-0 flex items-center space-x-3">
              <div className="relative">
                <div className="w-10 h-10 bg-gradient-to-br from-neon-orange-500 to-neon-orange-600 rounded-xl flex items-center justify-center neon-glow animate-pulse">
                  <span className="text-cyber-black font-bold text-lg font-mono">AI</span>
                </div>
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-neon-orange-400 rounded-full animate-ping"></div>
              </div>
              <div>
                <h1 className="text-xl font-bold cyber-heading">
                  Human-AI Co-Creation
                </h1>
                <p className="text-xs cyber-subheading hidden sm:block">
                  Collaborative Intelligence Platform
                </p>
              </div>
            </div>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-4">
            {/* Session Selector */}
            {user && sessionList.length > 0 && (
              <div className="relative" ref={sessionDropdownRef}>
                <button
                  onClick={() => setIsSessionDropdownOpen(!isSessionDropdownOpen)}
                  className="cyber-button px-4 py-2 rounded-lg font-medium transition-all duration-300 flex items-center space-x-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  <span>{currentSession ? formatSessionName(currentSession).substring(0, 20) + '...' : 'Select Session'}</span>
                  <svg
                    className={`w-4 h-4 transition-transform ${
                      isSessionDropdownOpen ? 'rotate-180' : ''
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {isSessionDropdownOpen && (
                  <div className="absolute right-0 mt-2 w-80 glass-strong rounded-xl shadow-cyber py-2 z-10 max-h-80 overflow-y-auto border-cyber">
                    <div className="px-4 py-3 text-sm font-medium cyber-subheading border-b border-neon-orange-500/20">
                      Select Session
                    </div>
                    {sessionList.map((session) => (
                      <button
                        key={session.session_id}
                        onClick={() => {
                          onSessionChange?.(session);
                          setIsSessionDropdownOpen(false);
                        }}
                        className={`block w-full text-left px-4 py-3 text-sm hover:glass transition-all duration-300 ${
                          currentSession?.session_id === session.session_id 
                            ? 'bg-neon-orange-500/10 text-neon-orange-300 border-r-2 border-neon-orange-500' 
                            : 'text-white hover:text-neon-orange-300'
                        }`}
                      >
                        <div className="font-medium">{formatSessionName(session)}</div>
                        <div className="text-xs text-cyber-gray-400 mt-1">
                          {formatSessionTime(session)}
                        </div>
                        {session.status && (
                          <div className="text-xs mt-1">
                            <span className={`px-2 py-1 rounded-full ${
                              session.status === 'active' 
                                ? 'bg-neon-orange-500/20 text-neon-orange-300' 
                                : 'bg-cyber-gray-600/20 text-cyber-gray-400'
                            }`}>
                              {session.status}
                            </span>
                          </div>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* User Menu */}
            {user ? (
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="cyber-button px-4 py-2 rounded-lg font-medium transition-all duration-300 flex items-center space-x-3"
                >
                  {user.picture ? (
                    <img
                      src={user.picture}
                      alt={user.name}
                      className="w-8 h-8 rounded-full ring-2 ring-neon-orange-500/50 neon-glow"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.nextSibling.style.display = 'flex';
                      }}
                    />
                  ) : (
                    <div className="w-8 h-8 bg-gradient-to-br from-neon-orange-500 to-neon-orange-600 rounded-full flex items-center justify-center ring-2 ring-neon-orange-500/50 neon-glow">
                      <span className="text-sm font-medium text-cyber-black">
                        {user.name?.charAt(0)?.toUpperCase() || 'U'}
                      </span>
                    </div>
                  )}
                  <div className="hidden lg:block text-left">
                    <div className="text-sm font-medium text-white">{user.name}</div>
                    <div className="text-xs cyber-subheading">{user.email}</div>
                  </div>
                  <svg
                    className={`w-4 h-4 transition-transform ${
                      isDropdownOpen ? 'rotate-180' : ''
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                
                {isDropdownOpen && (
                  <div className="absolute right-0 mt-2 w-64 glass-strong rounded-xl shadow-cyber py-2 z-10 border-cyber">
                    <div className="px-4 py-3 text-sm border-b border-neon-orange-500/20">
                      <div className="font-medium text-white">{user.name}</div>
                      <div className="cyber-subheading truncate">{user.email}</div>
                    </div>
                    
                    <div className="py-1">
                      <button
                        onClick={() => {
                          setIsDropdownOpen(false);
                        }}
                        className="block w-full text-left px-4 py-2 text-sm text-white hover:glass transition-all duration-300"
                      >
                        <div className="flex items-center space-x-2">
                          <svg className="w-4 h-4 text-neon-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                          </svg>
                          <span>Profile</span>
                        </div>
                      </button>
                      
                      <button
                        onClick={() => {
                          setIsDropdownOpen(false);
                        }}
                        className="block w-full text-left px-4 py-2 text-sm text-white hover:glass transition-all duration-300"
                      >
                        <div className="flex items-center space-x-2">
                          <svg className="w-4 h-4 text-neon-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          </svg>
                          <span>Settings</span>
                        </div>
                      </button>
                    </div>
                    
                    <div className="border-t border-neon-orange-500/20 pt-1">
                      <button
                        onClick={() => {
                          setIsDropdownOpen(false);
                          onSignOut();
                        }}
                        className="block w-full text-left px-4 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-all duration-300"
                      >
                        <div className="flex items-center space-x-2">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                          </svg>
                          <span>Sign out</span>
                        </div>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center space-x-2 cyber-subheading">
                <svg className="w-5 h-5 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <span>Please sign in</span>
              </div>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="cyber-button p-2 rounded-lg transition-all duration-300"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {isMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {isMenuOpen && (
          <div className="md:hidden border-t border-neon-orange-500/20 py-4 glass-strong">
            {user ? (
              <div className="space-y-4">
                <div className="flex items-center space-x-3 px-2">
                  {user.picture ? (
                    <img src={user.picture} alt={user.name} className="w-10 h-10 rounded-full neon-glow" />
                  ) : (
                    <div className="w-10 h-10 bg-gradient-to-br from-neon-orange-500 to-neon-orange-600 rounded-full flex items-center justify-center neon-glow">
                      <span className="text-cyber-black font-medium">
                        {user.name?.charAt(0)?.toUpperCase() || 'U'}
                      </span>
                    </div>
                  )}
                  <div>
                    <div className="text-white font-medium">{user.name}</div>
                    <div className="cyber-subheading text-sm">{user.email}</div>
                  </div>
                </div>
                
                {currentSession && (
                  <div className="px-2">
                    <div className="cyber-subheading text-sm">Current Session</div>
                    <div className="text-white">{formatSessionName(currentSession)}</div>
                  </div>
                )}
                
                <button
                  onClick={() => {
                    setIsMenuOpen(false);
                    onSignOut();
                  }}
                  className="block w-full text-left px-2 py-2 text-red-400 hover:text-red-300 transition-colors"
                >
                  Sign out
                </button>
              </div>
            ) : (
              <div className="px-2 cyber-subheading">
                Please sign in to continue
              </div>
            )}
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
