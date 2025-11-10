import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authFetch, parseAuthError, getErrorRedirectUrl } from '../utils/auth';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const Callback = ({ onAuthSuccess, onAuthFailure }) => {
  const [status, setStatus] = useState('processing'); // processing, validating, exchanging, success, error
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [userInfo, setUserInfo] = useState(null);
  const [redirectCountdown, setRedirectCountdown] = useState(null);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const abortControllerRef = useRef(null);

  useEffect(() => {
    const handleCallback = async () => {
      // Create abort controller for request cancellation
      abortControllerRef.current = new AbortController();
      
      try {
        setProgress(10);
        setStatus('validating');
        
        // Extract parameters
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');
        const errorDescription = searchParams.get('error_description');

        // Handle OAuth errors
        if (error) {
          let friendlyError = 'Authentication was cancelled or failed.';
          
          switch (error) {
            case 'access_denied':
              friendlyError = 'Access was denied. You need to grant permission to continue.';
              break;
            case 'invalid_request':
              friendlyError = 'Invalid authentication request. Please try again.';
              break;
            case 'temporarily_unavailable':
              friendlyError = 'Authentication service is temporarily unavailable. Please try again later.';
              break;
            default:
              if (errorDescription) {
                friendlyError = errorDescription;
              }
              break;
          }
          
          throw new Error(friendlyError);
        }

        if (!code) {
          throw new Error('No authorization code received. Please try signing in again.');
        }

        setProgress(30);
        setStatus('exchanging');

        // Exchange code for tokens with improved error handling
        const callbackUrl = new URL(`${API_BASE_URL}/auth/google/callback`);
        callbackUrl.searchParams.set('code', code);
        if (state) {
          callbackUrl.searchParams.set('state', state);
        }

        const response = await authFetch(callbackUrl.toString(), {
          method: 'GET',
          credentials: 'include',
        });

        setProgress(60);

        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          const userFriendlyError = parseAuthError(errorData?.detail || errorData?.message, response);
          throw new Error(userFriendlyError);
        }

        const data = await response.json();
        setProgress(80);

        if (!data.user) {
          throw new Error('User information not received from server.');
        }

        setUserInfo(data.user);
        
        // Poll /api/me to confirm session is established
        const maxPolls = 5;
        const pollInterval = 200; // Start with 200ms
        
        const pollMe = async (attemptNumber) => {
          try {
            const meResponse = await fetch(`${API_BASE_URL}/api/me`, {
              credentials: 'include',
              headers: { 'Content-Type': 'application/json' }
            });
            
            if (meResponse.ok) {
              const meData = await meResponse.json();
              console.log('✅ Session confirmed:', meData);
              return true;
            }
            return false;
          } catch (e) {
            console.warn(`/api/me poll attempt ${attemptNumber + 1} failed:`, e);
            return false;
          }
        };
        
        // Try polling with exponential backoff
        let sessionConfirmed = false;
        for (let i = 0; i < maxPolls && !sessionConfirmed; i++) {
          sessionConfirmed = await pollMe(i);
          
          if (!sessionConfirmed && i < maxPolls - 1) {
            await new Promise(resolve => setTimeout(resolve, pollInterval * Math.pow(2, i)));
          }
        }
        
        if (!sessionConfirmed) {
          console.warn('Session confirmation polling timed out, but proceeding with login');
        }
        
        setProgress(100);
        setStatus('success');

        // Start countdown for redirect
        let countdown = 3;
        setRedirectCountdown(countdown);
        
        const redirectTimer = setInterval(() => {
          countdown--;
          setRedirectCountdown(countdown);
          
          if (countdown <= 0) {
            clearInterval(redirectTimer);
            onAuthSuccess?.(data.user);
            navigate('/', { replace: true });
          }
        }, 1000);

        // Cleanup function will clear the timer if component unmounts
        return () => clearInterval(redirectTimer);

      } catch (err) {
        if (err.name === 'AbortError') {
          // Request was cancelled, don't update state
          return;
        }
        
        console.error('Callback handling error:', err);
        const userFriendlyError = parseAuthError(err);
        setError(userFriendlyError);
        setStatus('error');
        setProgress(0);
        onAuthFailure?.(err);
        
        // Auto-redirect to login after a delay for better UX
        setTimeout(() => {
          navigate(getErrorRedirectUrl(err), { replace: true });
        }, 5000);
      }
    };

    handleCallback();

    // Cleanup function
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [searchParams, navigate, onAuthSuccess, onAuthFailure]);

  const retryAuth = () => {
    navigate('/login', { replace: true });
  };

  const getStatusConfig = () => {
    switch (status) {
      case 'processing':
      case 'validating':
        return {
          icon: (
            <svg className="w-8 h-8 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          ),
          title: 'Validating Authentication',
          subtitle: 'Verifying your credentials...',
          color: 'text-neon-orange-400'
        };
      case 'exchanging':
        return {
          icon: (
            <svg className="w-8 h-8 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          ),
          title: 'Exchanging Tokens',
          subtitle: 'Securing your session...',
          color: 'text-blue-400'
        };
      case 'success':
        return {
          icon: (
            <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ),
          title: 'Authentication Successful',
          subtitle: 'Welcome to the platform!',
          color: 'text-green-400'
        };
      case 'error':
        return {
          icon: (
            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.732 18.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          ),
          title: 'Authentication Failed',
          subtitle: 'Please try again',
          color: 'text-red-400'
        };
      default:
        return {
          icon: null,
          title: 'Processing...',
          subtitle: '',
          color: 'text-cyber-gray-400'
        };
    }
  };

  const statusConfig = getStatusConfig();

  return (
    <div className="min-h-screen bg-cyber-black cyber-grid flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Main Status Card */}
        <div className="glass-strong rounded-2xl p-8 shadow-cyber border-cyber liquid-morph text-center">
          {/* Logo */}
          <div className="relative mx-auto w-16 h-16 mb-8">
            <div className="w-16 h-16 bg-gradient-to-br from-neon-orange-500 to-neon-orange-600 rounded-2xl flex items-center justify-center neon-glow-strong animate-pulse">
              <span className="text-cyber-black font-bold text-2xl font-mono">AI</span>
            </div>
            <div className="absolute -top-2 -right-2 w-6 h-6 bg-neon-orange-400 rounded-full animate-ping"></div>
          </div>

          {/* Status Icon */}
          <div className={`mb-6 ${statusConfig.color} flex justify-center`}>
            {statusConfig.icon}
          </div>

          {/* Status Text */}
          <h2 className="text-xl font-semibold text-white mb-2">
            {statusConfig.title}
          </h2>
          <p className="cyber-subheading mb-6">
            {statusConfig.subtitle}
          </p>

          {/* Progress Bar */}
          {status !== 'error' && (
            <div className="mb-6">
              <div className="w-full bg-cyber-gray-600/30 rounded-full h-2">
                <div 
                  className="bg-gradient-to-r from-neon-orange-500 to-neon-orange-400 h-2 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <p className="text-xs cyber-subheading mt-2">
                {Math.round(progress)}% complete
              </p>
            </div>
          )}

          {/* User Info Display */}
          {status === 'success' && userInfo && (
            <div className="glass rounded-xl p-4 border-cyber mb-6">
              <div className="flex items-center space-x-3">
                {userInfo.picture ? (
                  <img 
                    src={userInfo.picture} 
                    alt={userInfo.name}
                    className="w-12 h-12 rounded-full ring-2 ring-neon-orange-500/50 neon-glow"
                  />
                ) : (
                  <div className="w-12 h-12 bg-gradient-to-br from-neon-orange-500 to-neon-orange-600 rounded-full flex items-center justify-center neon-glow">
                    <span className="text-cyber-black font-medium">
                      {userInfo.name?.charAt(0)?.toUpperCase() || 'U'}
                    </span>
                  </div>
                )}
                <div className="text-left">
                  <p className="text-white font-medium">{userInfo.name}</p>
                  <p className="cyber-subheading text-sm">{userInfo.email}</p>
                </div>
              </div>
            </div>
          )}

          {/* Redirect Countdown */}
          {redirectCountdown !== null && status === 'success' && (
            <div className="glass rounded-xl p-4 border-cyber mb-6">
              <div className="flex items-center justify-center space-x-2">
                <svg className="w-5 h-5 text-neon-orange-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-white">
                  Redirecting in <span className="text-neon-orange-400 font-bold">{redirectCountdown}</span> seconds
                </p>
              </div>
            </div>
          )}

          {/* Error Display */}
          {error && status === 'error' && (
            <div className="glass rounded-xl p-4 border-red-500/30 bg-red-500/10 mb-6">
              <p className="text-red-300 text-sm leading-relaxed">
                {error}
              </p>
            </div>
          )}

          {/* Action Buttons */}
          {status === 'error' && (
            <div className="space-y-3">
              <button
                onClick={retryAuth}
                className="w-full cyber-button px-6 py-3 rounded-xl font-medium hover:scale-105 transform transition-all duration-300"
              >
                <svg className="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Try Again
              </button>
              <button
                onClick={() => navigate('/login', { replace: true })}
                className="w-full cyber-button px-6 py-3 rounded-xl font-medium bg-cyber-gray-600/20 hover:bg-cyber-gray-600/40 border-cyber-gray-500/30 hover:scale-105 transform transition-all duration-300"
              >
                <svg className="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 17l-5-5m0 0l5-5m-5 5h12" />
                </svg>
                Back to Login
              </button>
            </div>
          )}

          {status === 'success' && (
            <button
              onClick={() => {
                onAuthSuccess?.(userInfo);
                navigate('/', { replace: true });
              }}
              className="w-full cyber-button px-6 py-3 rounded-xl font-medium hover:scale-105 transform transition-all duration-300"
            >
              <svg className="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
              Continue to Platform
            </button>
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-6">
          <p className="cyber-subheading text-xs">
            Secure authentication powered by Google OAuth 2.0
          </p>
        </div>
      </div>

      {/* Background Elements */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        {/* Animated orbs */}
        <div className="absolute top-1/4 left-1/4 w-32 h-32 bg-neon-orange-500/10 rounded-full animate-float blur-xl"></div>
        <div className="absolute top-3/4 right-1/4 w-48 h-48 bg-neon-orange-400/5 rounded-full animate-float animation-delay-2000 blur-2xl"></div>
        <div className="absolute top-1/2 left-3/4 w-24 h-24 bg-neon-orange-600/10 rounded-full animate-float animation-delay-4000 blur-lg"></div>
        
        {/* Processing particles for loading states */}
        {(status === 'processing' || status === 'validating' || status === 'exchanging') && (
          <div className="absolute inset-0 overflow-hidden">
            {[...Array(6)].map((_, i) => (
              <div
                key={i}
                className="absolute w-2 h-2 bg-neon-orange-400 rounded-full animate-ping"
                style={{
                  top: `${20 + Math.random() * 60}%`,
                  left: `${20 + Math.random() * 60}%`,
                  animationDelay: `${i * 0.5}s`,
                  animationDuration: '2s'
                }}
              ></div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Callback;
