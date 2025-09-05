import React, { useState, useEffect } from 'react';
import { BACKEND_PORT } from '../config/constants';
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || `http://localhost:${BACKEND_PORT}`;

const AuthGoogle = ({ onAuthStart, onAuthComplete, onAuthError }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const maxRetries = 3;

  // Network status detection
  useEffect(() => {
    const handleOnline = () => {
      setIsOffline(false);
      setError(null);
    };
    const handleOffline = () => {
      setIsOffline(true);
      setError('You appear to be offline. Please check your internet connection.');
    };
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Clear error after some time
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        setError(null);
      }, 10000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const handleGoogleLogin = async () => {
    if (isOffline) {
      setError('You appear to be offline. Please check your internet connection and try again.');
      return;
    }

    setIsLoading(true);
    setError(null);
    let attempts = 0;
    const maxAttempts = maxRetries;
    while (attempts < maxAttempts) {
      try {
        onAuthStart?.();
        // Check if server is reachable
        const healthResponse = await fetch(`${API_BASE_URL}/health`, { method: 'GET' });
        if (!healthResponse.ok) {
          throw new Error('Server health check failed');
        }
        // Initiate Google OAuth flow
        const response = await fetch(`${API_BASE_URL}/api/auth/google`, {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          }
        });
        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          throw new Error(errorData?.detail || `Authentication failed (${response.status})`);
        }
        const data = await response.json();
        if (data.auth_url) {
          window.location.href = data.auth_url;
          return;
        } else {
          throw new Error('No authentication URL received from server');
        }
      } catch (err) {
        attempts++;
        let errorMessage = 'Authentication failed. Please try again.';
        if (err.name === 'TypeError' && err.message.includes('fetch')) {
          errorMessage = 'Cannot connect to authentication server. Please check your connection and try again.';
        } else if (err.message.includes('timeout') || err.message.includes('ECONNREFUSED')) {
          errorMessage = 'Connection timeout. Please check if the server is running and try again.';
        } else if (err.message) {
          errorMessage = err.message;
        }
        setError(errorMessage);
        setRetryCount(prev => prev + 1);
        onAuthError?.(err);
        if (attempts < maxAttempts) {
          await new Promise(res => setTimeout(res, 1000 * attempts)); // Exponential backoff
        }
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleRetry = () => {
    if (retryCount < maxRetries) {
      handleGoogleLogin();
    } else {
      setError('Maximum retry attempts reached. Please refresh the page and try again.');
    }
  };

  return (
    <div className="min-h-screen bg-cyber-black cyber-grid flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Main Auth Card */}
        <div className="glass-strong rounded-2xl p-8 shadow-cyber border-cyber liquid-morph">
          {/* Logo/Branding */}
          <div className="text-center mb-8">
            <div className="relative mx-auto w-16 h-16 mb-6">
              <div className="w-16 h-16 bg-gradient-to-br from-neon-orange-500 to-neon-orange-600 rounded-2xl flex items-center justify-center neon-glow-strong animate-pulse">
                <span className="text-cyber-black font-bold text-2xl font-mono">AI</span>
              </div>
              <div className="absolute -top-2 -right-2 w-6 h-6 bg-neon-orange-400 rounded-full animate-ping"></div>
            </div>
            <h1 className="text-3xl font-bold cyber-heading mb-2">
              Human-AI Co-Creation
            </h1>
            <p className="cyber-subheading">
              Collaborative Intelligence Platform
            </p>
          </div>

          {/* Status Messages */}
          {isOffline && (
            <div className="glass rounded-xl p-4 border-red-500/30 bg-red-500/10 mb-6">
              <div className="flex items-center space-x-3">
                <svg className="w-5 h-5 text-red-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.732 18.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <div>
                  <p className="text-red-300 font-medium">Connection Issue</p>
                  <p className="text-red-400 text-sm">Please check your internet connection</p>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="glass rounded-xl p-4 border-red-500/30 bg-red-500/10 mb-6">
              <div className="flex items-start space-x-3">
                <svg className="w-5 h-5 text-red-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.732 18.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <div className="flex-1">
                  <p className="text-red-300 font-medium">Authentication Error</p>
                  <p className="text-red-400 text-sm leading-relaxed">{error}</p>
                  {retryCount < maxRetries && (
                    <button
                      onClick={handleRetry}
                      className="mt-3 cyber-button px-4 py-2 rounded-lg text-sm hover:scale-105 transform transition-all duration-300"
                    >
                      Retry ({maxRetries - retryCount} attempts left)
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Authentication Section */}
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-white mb-2">Welcome Back</h2>
              <p className="cyber-subheading text-sm">
                Sign in to continue your creative journey
              </p>
              <div className="mt-4 pt-4 border-t border-cyber-gray-600/30">
                <p className="cyber-subheading text-xs">
                  New to the platform? <span className="text-neon-orange-400">No account needed!</span>
                  <br />
                  Google will create your account automatically
                </p>
              </div>
            </div>

            {/* Google Sign In Button */}
            <button
              onClick={handleGoogleLogin}
              disabled={isLoading || isOffline}
              className={`w-full cyber-button px-6 py-4 rounded-xl font-medium transition-all duration-300 flex items-center justify-center space-x-3 ${
                isLoading ? 'cyber-pulse' : 'hover:scale-105 hover:neon-glow-strong'
              } ${isOffline ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {isLoading ? (
                <>
                  <svg className="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  <span>Connecting...</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  <span>Continue with Google</span>
                </>
              )}
            </button>

            {/* Additional Options */}
            <div className="text-center space-y-3">
              <p className="cyber-subheading text-xs">
                One click for both <span className="text-neon-orange-400 font-medium">Sign In</span> and <span className="text-neon-orange-400 font-medium">Sign Up</span>
              </p>
              <div className="flex items-center justify-center space-x-4 text-xs cyber-subheading">
                <span className="flex items-center space-x-1">
                  <svg className="w-3 h-3 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span>Existing Users</span>
                </span>
                <span className="flex items-center space-x-1">
                  <svg className="w-3 h-3 text-neon-orange-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clipRule="evenodd" />
                  </svg>
                  <span>New Users</span>
                </span>
              </div>
            </div>

            {/* Security Notice */}
            <div className="glass rounded-lg p-4 border-cyber">
              <div className="flex items-start space-x-3">
                <svg className="w-5 h-5 text-neon-orange-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <div>
                  <p className="text-white font-medium text-sm">Secure Authentication</p>
                  <p className="cyber-subheading text-xs leading-relaxed mt-1">
                    Your data is protected with enterprise-grade security. We only access basic profile information.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-8">
          <p className="cyber-subheading text-sm">
            By signing in, you agree to our terms of service and privacy policy
          </p>
          <div className="flex justify-center space-x-6 mt-4">
            <a href="#" className="cyber-subheading text-xs hover:text-neon-orange-400 transition-colors">
              Privacy Policy
            </a>
            <a href="#" className="cyber-subheading text-xs hover:text-neon-orange-400 transition-colors">
              Terms of Service
            </a>
            <a href="#" className="cyber-subheading text-xs hover:text-neon-orange-400 transition-colors">
              Support
            </a>
          </div>
        </div>
      </div>

      {/* Background Elements */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        {/* Floating orbs */}
        <div className="absolute top-1/4 left-1/4 w-32 h-32 bg-neon-orange-500/10 rounded-full animate-float blur-xl"></div>
        <div className="absolute top-3/4 right-1/4 w-48 h-48 bg-neon-orange-400/5 rounded-full animate-float animation-delay-2000 blur-2xl"></div>
        <div className="absolute top-1/2 left-3/4 w-24 h-24 bg-neon-orange-600/10 rounded-full animate-float animation-delay-4000 blur-lg"></div>
      </div>
    </div>
  );
};

export default AuthGoogle;
