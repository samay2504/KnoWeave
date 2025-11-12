import React, { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth } from '../utils/api';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const HealthCheck = () => {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval] = useState(30000);
  const [lastChecked, setLastChecked] = useState(null);

  const checkHealth = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    setError(null);
    
    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/health/detailed`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setHealth(data);
        setLastChecked(new Date());
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
    } catch (err) {
      console.error('Health check failed:', err);
      setError(
        err.message || 'Health check failed. Check if backend is running.'
      );
      setHealth(null);
    } finally {
      if (showLoading) setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth(true);
    
    // Auto-refresh with configurable interval
    let interval;
    if (autoRefresh) {
      interval = setInterval(() => checkHealth(false), refreshInterval);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [checkHealth, autoRefresh, refreshInterval]);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
      case 'up':
        return { 
          icon: '✓',
          color: 'text-green-400',
          bg: 'bg-green-500/20',
          border: 'border-green-500/30'
        };
      case 'degraded':
        return { 
          icon: '⚠',
          color: 'text-yellow-400',
          bg: 'bg-yellow-500/20',
          border: 'border-yellow-500/30'
        };
      case 'unhealthy':
      case 'down':
        return { 
          icon: '✕',
          color: 'text-red-400',
          bg: 'bg-red-500/20',
          border: 'border-red-500/30'
        };
      default:
        return { 
          icon: '?',
          color: 'text-gray-400',
          bg: 'bg-gray-500/20',
          border: 'border-gray-500/30'
        };
    }
  };

  const formatUptime = (seconds) => {
    if (!seconds || seconds === 0) return 'Unknown';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  const formatTime = (date) => {
    if (!date) return 'Unknown';
    
    try {
      // Convert to Date object if it's a string or timestamp
      const dateObj = date instanceof Date ? date : new Date(date);
      
      // Check if valid date
      if (isNaN(dateObj.getTime())) return 'Invalid time';
      
      // Format time: HH:MM:SS AM/PM
      return dateObj.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      });
    } catch (e) {
      console.error('Error formatting time:', e);
      return 'Time error';
    }
  };

  const getOverallStatus = () => {
    if (!health) return 'unknown';
    if (health.status === 'healthy' || health.status === 'up') return 'healthy';
    if (health.warnings && health.warnings.length > 0) return 'degraded';
    return health.status || 'unknown';
  };

  const overallStatus = getOverallStatus();
  const statusInfo = getStatusIcon(overallStatus);

  return (
    <div className="glass-strong rounded-xl p-6 border-cyber shadow-cyber">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold cyber-heading flex items-center">
          <div className={`w-3 h-3 rounded-full mr-3 animate-pulse ${
            overallStatus === 'healthy' ? 'bg-green-400' : 
            overallStatus === 'degraded' ? 'bg-yellow-400' : 
            overallStatus === 'unhealthy' ? 'bg-red-400' : 'bg-gray-400'
          }`}></div>
          System Health
        </h3>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => checkHealth(true)}
            disabled={loading}
            className="cyber-button p-2 rounded-lg hover:scale-110 transform transition-all duration-300"
            title="Refresh now"
          >
            <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="cyber-button p-2 rounded-lg text-xs"
            title={expanded ? 'Show less' : 'Show more'}
          >
            More
          </button>
        </div>
      </div>

      {loading && !health ? (
        <div className="space-y-3 animate-pulse">
          <div className="h-4 bg-gray-700/50 rounded w-1/2"></div>
          <div className="h-3 bg-gray-700/30 rounded w-3/4"></div>
        </div>
      ) : error ? (
        <div className="text-center py-4">
          <div className="text-red-400 text-2xl mb-2">⚠</div>
          <p className="text-red-400 text-sm mb-3">{error}</p>
          <button
            onClick={() => checkHealth(true)}
            className="cyber-button px-4 py-2 rounded-lg text-sm"
          >
            Retry
          </button>
        </div>
      ) : health ? (
        <>
          {/* Status Display */}
          <div className={`glass rounded-lg p-4 border ${statusInfo.border} ${statusInfo.bg} mb-4`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className={`text-2xl ${statusInfo.color}`}>{statusInfo.icon}</span>
                <div>
                  <div className="text-white font-medium capitalize">{overallStatus}</div>
                  <div className="text-xs text-gray-400">
                    Last checked: {formatTime(lastChecked)}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="glass rounded-lg p-3 border-cyber">
              <div className="text-xs text-gray-400 mb-1">Mongo</div>
              <div className={`flex items-center space-x-1 ${
                health.services?.mongo === 'healthy' ? 'text-green-400' : 'text-red-400'
              }`}>
                <span className="text-lg">{health.services?.mongo === 'healthy' ? '✓' : '✕'}</span>
              </div>
            </div>
            <div className="glass rounded-lg p-3 border-cyber">
              <div className="text-xs text-gray-400 mb-1">Arango</div>
              <div className={`flex items-center space-x-1 ${
                health.services?.arango === 'healthy' ? 'text-green-400' : 'text-red-400'
              }`}>
                <span className="text-lg">{health.services?.arango === 'healthy' ? '✓' : '✕'}</span>
              </div>
            </div>
            <div className="glass rounded-lg p-3 border-cyber">
              <div className="text-xs text-gray-400 mb-1">LLM</div>
              <div className={`flex items-center space-x-1 ${
                health.services?.llm === 'healthy' ? 'text-green-400' : 'text-red-400'
              }`}>
                <span className="text-lg">{health.services?.llm === 'healthy' ? '✓' : '✕'}</span>
              </div>
            </div>
            <div className="glass rounded-lg p-3 border-cyber">
              <div className="text-xs text-gray-400 mb-1">JSON Fallback</div>
              <div className={`flex items-center space-x-1 ${
                health.services?.json_fallback === 'healthy' ? 'text-green-400' : 'text-red-400'
              }`}>
                <span className="text-lg">{health.services?.json_fallback === 'healthy' ? '✓' : '✕'}</span>
              </div>
            </div>
          </div>

          {/* Expanded Details */}
          {expanded && (
            <div className="mt-4 space-y-3">
              <div className="glass rounded-lg p-3 border-cyber">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-400">Version</span>
                  <span className="text-white font-mono text-sm">{health.version || 'Unknown'}</span>
                </div>
              </div>
              <div className="glass rounded-lg p-3 border-cyber">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-400">Uptime</span>
                  <span className="text-green-400 font-medium text-sm">{formatUptime(health.uptime)}</span>
                </div>
              </div>
              {health.warnings && health.warnings.length > 0 && (
                <div className="glass rounded-lg p-3 border-yellow-500/30 bg-yellow-500/10">
                  <div className="text-xs text-yellow-400 font-medium mb-2">⚠ Warnings</div>
                  {health.warnings.map((warning, i) => (
                    <div key={i} className="text-xs text-yellow-300">• {warning}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-4">
          <div className="text-gray-500 text-2xl mb-2">?</div>
          <p className="text-gray-400 text-sm">Status unknown</p>
          <p className="text-xs text-gray-500 mt-1">Click refresh to check</p>
        </div>
      )}
    </div>
  );
};

export default HealthCheck;
