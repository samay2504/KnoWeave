import React, { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth } from '../utils/api';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const HealthCheck = () => {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30000);

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
        return { icon: '✅', color: 'text-green-400' };
      case 'degraded':
        return { icon: '⚠️', color: 'text-yellow-400' };
      case 'unhealthy':
      case 'down':
        return { icon: '❌', color: 'text-red-400' };
      default:
        return { icon: '❓', color: 'text-gray-400' };
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy':
      case 'up':
        return 'border-green-400 bg-green-900/20';
      case 'degraded':
        return 'border-yellow-400 bg-yellow-900/20';
      case 'unhealthy':
      case 'down':
        return 'border-red-400 bg-red-900/20';
      default:
        return 'border-gray-400 bg-gray-900/20';
    }
  };

  const formatUptime = (seconds) => {
    if (!seconds) return 'Unknown';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  if (loading) {
    return (
      <div className="p-6 bg-gray-900 rounded-lg border border-gray-700">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="space-y-2">
            <div className="h-3 bg-gray-700 rounded w-3/4"></div>
            <div className="h-3 bg-gray-700 rounded w-1/2"></div>
            <div className="h-3 bg-gray-700 rounded w-2/3"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-900 rounded-lg border border-gray-700">
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center space-x-3">
          <h3 className="text-lg font-medium text-white">System Health</h3>
          {health && (
            <span className={`${getStatusIcon(health.status).color} text-lg`}>
              {getStatusIcon(health.status).icon}
            </span>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`text-xs px-2 py-1 rounded ${
              autoRefresh 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            } transition-colors`}
          >
            {autoRefresh ? 'Auto' : 'Manual'}
          </button>
          
          <select
            value={refreshInterval}
            onChange={(e) => setRefreshInterval(Number(e.target.value))}
            className="text-xs bg-gray-700 text-white border border-gray-600 rounded px-2 py-1"
            disabled={!autoRefresh}
          >
            <option value={10000}>10s</option>
            <option value={30000}>30s</option>
            <option value={60000}>1m</option>
            <option value={300000}>5m</option>
          </select>
          
          <button
            onClick={() => checkHealth(true)}
            disabled={loading}
            className="text-xs px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Refresh
          </button>
          
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs px-2 py-1 bg-gray-700 text-gray-300 rounded hover:bg-gray-600 transition-colors"
          >
            {expanded ? 'Collapse' : 'Expand'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/20 border border-red-400 rounded-lg">
          <div className="flex items-center space-x-2 text-red-400 text-sm font-medium mb-1">
            <span>❌</span>
            <span>Health Check Failed</span>
          </div>
          <p className="text-red-300 text-sm">{error}</p>
          <p className="text-red-200 text-xs mt-1">
            Falling back to basic connectivity check...
          </p>
        </div>
      )}

      {health && (
        <div className={`border rounded-lg p-4 ${getStatusColor(health.status)}`}>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">
                {health.status || 'Unknown'}
              </div>
              <div className="text-sm text-gray-400">Overall Status</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-white">
                {formatUptime(health.uptime)}
              </div>
              <div className="text-sm text-gray-400">Uptime</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-white">
                {health.timestamp ? new Date(health.timestamp).toLocaleTimeString() : 'Unknown'}
              </div>
              <div className="text-sm text-gray-400">Last Check</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-white">
                {health.version || 'Unknown'}
              </div>
              <div className="text-sm text-gray-400">Version</div>
            </div>
          </div>

          {expanded && (
            <div className="space-y-4">
              {/* Environment Info */}
              {health.environment && (
                <div>
                  <h4 className="text-white font-medium mb-2">Environment</h4>
                  <div className="bg-gray-800/50 rounded p-3 text-sm">
                    <div className="grid grid-cols-2 gap-2">
                      <div><span className="text-gray-400">Mode:</span> <span className="text-white">{health.environment.mode || 'Unknown'}</span></div>
                      <div><span className="text-gray-400">Debug:</span> <span className="text-white">{health.environment.debug ? 'Enabled' : 'Disabled'}</span></div>
                    </div>
                  </div>
                </div>
              )}

              {/* Services Status */}
              {health.services && Object.keys(health.services).length > 0 && (
                <div>
                  <h4 className="text-white font-medium mb-2">Services</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {Object.entries(health.services).map(([serviceName, serviceStatus]) => {
                      const { icon, color } = getStatusIcon(typeof serviceStatus === 'object' ? serviceStatus.status : serviceStatus);
                      return (
                        <div key={serviceName} className="bg-gray-800/50 rounded p-3 flex items-center justify-between">
                          <span className="text-white capitalize">{serviceName}</span>
                          <div className="flex items-center space-x-2">
                            <span className={color}>{icon}</span>
                            <span className="text-gray-300 text-sm">
                              {typeof serviceStatus === 'object' ? serviceStatus.status : serviceStatus}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Database Status */}
              {health.database && (
                <div>
                  <h4 className="text-white font-medium mb-2">Database</h4>
                  <div className="bg-gray-800/50 rounded p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-white">Connection Status</span>
                      <div className="flex items-center space-x-2">
                        <span className={getStatusIcon(health.database.status).color}>
                          {getStatusIcon(health.database.status).icon}
                        </span>
                        <span className="text-gray-300">{health.database.status}</span>
                      </div>
                    </div>
                    {health.database.type && (
                      <div className="text-sm text-gray-400">
                        Type: {health.database.type}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Performance Metrics */}
              {health.performance && (
                <div>
                  <h4 className="text-white font-medium mb-2">Performance</h4>
                  <div className="bg-gray-800/50 rounded p-3">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      {health.performance.response_time && (
                        <div>
                          <div className="text-gray-400">Response Time</div>
                          <div className="text-white font-medium">{health.performance.response_time}ms</div>
                        </div>
                      )}
                      {health.performance.memory_usage && (
                        <div>
                          <div className="text-gray-400">Memory Usage</div>
                          <div className="text-white font-medium">{health.performance.memory_usage}%</div>
                        </div>
                      )}
                      {health.performance.cpu_usage && (
                        <div>
                          <div className="text-gray-400">CPU Usage</div>
                          <div className="text-white font-medium">{health.performance.cpu_usage}%</div>
                        </div>
                      )}
                      {health.performance.requests_per_minute && (
                        <div>
                          <div className="text-gray-400">Requests/min</div>
                          <div className="text-white font-medium">{health.performance.requests_per_minute}</div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Warnings */}
              {health.warnings && health.warnings.length > 0 && (
                <div>
                  <h4 className="text-white font-medium mb-2 flex items-center space-x-2">
                    <span>⚠️</span>
                    <span>Warnings</span>
                  </h4>
                  <div className="space-y-2">
                    {health.warnings.map((warning, index) => (
                      <div key={index} className="text-sm text-yellow-300 bg-yellow-900/20 border border-yellow-700 p-2 rounded">
                        {warning}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default HealthCheck;
