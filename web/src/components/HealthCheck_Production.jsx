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
    
    // Auto-refresh if enabled
    let intervalId;
    if (autoRefresh) {
      intervalId = setInterval(() => checkHealth(false), refreshInterval);
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [autoRefresh, refreshInterval, checkHealth]);

  const getStatusColor = (status) => {
    const statusColors = {
      'healthy': 'text-green-400',
      'connected': 'text-green-400',
      'ok': 'text-green-400',
      'available': 'text-green-400',
      'degraded': 'text-yellow-400',
      'warning': 'text-yellow-400',
      'not_configured': 'text-gray-400',
      'unknown': 'text-gray-400',
      'error': 'text-red-400',
      'timeout': 'text-red-400',
      'disconnected': 'text-red-400'
    };
    return statusColors[status] || 'text-gray-400';
  };

  const getStatusIcon = (status) => {
    const statusIcons = {
      'healthy': '✓',
      'connected': '✓',
      'ok': '✓',
      'available': '✓',
      'degraded': '⚠',
      'warning': '⚠',
      'not_configured': '○',
      'unknown': '?',
      'error': '✗',
      'timeout': '⏱',
      'disconnected': '✗'
    };
    return statusIcons[status] || '?';
  };

  if (loading && !health) {
    return (
      <div className="glass rounded-xl p-6 border-cyber">
        <div className="flex items-center space-x-3">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-neon-orange-500"></div>
          <p className="cyber-subheading">Checking system health...</p>
        </div>
      </div>
    );
  }

  if (error && !health) {
    return (
      <div className="glass rounded-xl p-6 border-cyber border-red-500/30">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-red-400">System Health - Error</h3>
          <button
            onClick={() => checkHealth(true)}
            className="cyber-button px-3 py-1 rounded text-sm"
          >
            Retry
          </button>
        </div>
        <p className="text-sm text-red-300">{error}</p>
      </div>
    );
  }

  if (!health) return null;

  return (
    <div className="glass rounded-xl p-6 border-cyber">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold cyber-heading flex items-center">
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          System Health
        </h3>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => checkHealth(true)}
            disabled={loading}
            className="cyber-button px-3 py-1 rounded text-sm hover:scale-105 transform transition-all duration-300"
            title="Refresh health status"
          >
            <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="cyber-button px-3 py-1 rounded text-sm hover:scale-105 transform transition-all duration-300"
          >
            {expanded ? 'Less' : 'More'}
          </button>
        </div>
      </div>

      {/* Overall Status */}
      <div className="mb-4">
        <div className="flex items-center space-x-2">
          <span className="text-xs cyber-subheading">Status:</span>
          <span className={`text-sm font-semibold ${getStatusColor(health.status)}`}>
            {getStatusIcon(health.status)} {health.status?.toUpperCase() || 'UNKNOWN'}
          </span>
        </div>
        <div className="flex items-center space-x-2 mt-1">
          <span className="text-xs cyber-subheading">Last checked:</span>
          <span className="text-xs text-white">
            {new Date(health.timestamp).toLocaleTimeString()}
          </span>
        </div>
        {health.response_time_ms && (
          <div className="flex items-center space-x-2 mt-1">
            <span className="text-xs cyber-subheading">Response time:</span>
            <span className="text-xs text-white">{health.response_time_ms}ms</span>
          </div>
        )}
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {health.services && Object.entries(health.services).map(([serviceName, serviceData]) => {
          const status = typeof serviceData === 'object' ? serviceData.status : serviceData;
          const message = typeof serviceData === 'object' ? serviceData.message : '';
          
          return (
            <div key={serviceName} className="p-3 glass rounded-lg border-cyber">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs cyber-subheading capitalize">{serviceName.replace('_', ' ')}</span>
                <span className={`text-lg ${getStatusColor(status)}`}>
                  {getStatusIcon(status)}
                </span>
              </div>
              {expanded && message && (
                <p className="text-xs text-cyber-gray-300 mt-1">{message}</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="space-y-3 mt-4 pt-4 border-t border-cyber-gray-600/30">
          {/* Agents Status */}
          {health.agents && (
            <div>
              <h4 className="text-sm font-semibold cyber-subheading mb-2">Agents</h4>
              <div className="grid grid-cols-3 gap-2">
                {Object.entries(health.agents).filter(([key]) => key !== 'total_count').map(([agentName, isActive]) => (
                  <div key={agentName} className="flex items-center space-x-2">
                    <span className={`text-xs ${isActive ? 'text-green-400' : 'text-gray-400'}`}>
                      {isActive ? '✓' : '○'}
                    </span>
                    <span className="text-xs text-white capitalize">{agentName.replace('_', ' ')}</span>
                  </div>
                ))}
              </div>
              <p className="text-xs cyber-subheading mt-2">
                Total: {health.agents.total_count} agents loaded
              </p>
            </div>
          )}

          {/* Active Sessions */}
          {health.active_sessions !== undefined && (
            <div>
              <h4 className="text-sm font-semibold cyber-subheading mb-2">Sessions</h4>
              <p className="text-xs text-white">
                Active sessions: <span className="text-neon-orange-400 font-bold">{health.active_sessions}</span>
              </p>
            </div>
          )}

          {/* Version */}
          {health.version && (
            <div>
              <h4 className="text-sm font-semibold cyber-subheading mb-2">Version</h4>
              <p className="text-xs text-white font-mono">{health.version}</p>
            </div>
          )}

          {/* Auto-refresh toggle */}
          <div className="flex items-center justify-between pt-2 border-t border-cyber-gray-600/30">
            <span className="text-xs cyber-subheading">Auto-refresh ({refreshInterval/1000}s)</span>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3 py-1 rounded text-xs transition-all duration-300 ${
                autoRefresh 
                  ? 'bg-neon-orange-500/20 text-neon-orange-300 border border-neon-orange-500/30' 
                  : 'bg-cyber-gray-600/20 text-cyber-gray-300 border border-cyber-gray-600/30'
              }`}
            >
              {autoRefresh ? 'On' : 'Off'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default HealthCheck;
