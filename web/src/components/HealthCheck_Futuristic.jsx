import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

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
      // Try detailed health endpoint first
      try {
        const response = await axios.get(`${API_BASE_URL}/api/health/detailed`, {
          timeout: 10000,
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          }
        });
        
        if (response.data) {
          setHealth({
            ...response.data,
            timestamp: new Date().toISOString()
          });
          return;
        }
      } catch (detailedError) {
        console.warn('Detailed health check failed, trying basic endpoint:', detailedError.message);
      }

      // Fallback to basic health endpoint
      const basicResponse = await axios.get(`${API_BASE_URL}/health`, {
        timeout: 5000,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      // Transform basic response to match expected format
      const basicHealth = basicResponse.data;
      setHealth({
        status: basicHealth.status || 'healthy',
        timestamp: new Date().toISOString(),
        version: basicHealth.version || 'Unknown',
        uptime: basicHealth.uptime || 0,
        services: basicHealth.services || {},
        database: basicHealth.database || { status: 'unknown' },
        environment: {
          mode: basicHealth.environment || 'production',
          debug: basicHealth.debug || false
        },
        performance: basicHealth.performance || {},
        warnings: basicHealth.warnings || []
      });
      
    } catch (err) {
      console.error('Health check failed:', err);
      setError(
        err.code === 'ECONNREFUSED' 
          ? 'Cannot connect to server. Please check if the backend is running.'
          : err.message || 'Health check failed'
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
          icon: (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ), 
          color: 'text-green-400',
          bg: 'bg-green-500/20',
          glow: 'shadow-green-400/50'
        };
      case 'degraded':
        return { 
          icon: (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.732 18.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          ), 
          color: 'text-yellow-400',
          bg: 'bg-yellow-500/20',
          glow: 'shadow-yellow-400/50'
        };
      case 'unhealthy':
      case 'down':
        return { 
          icon: (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ), 
          color: 'text-red-400',
          bg: 'bg-red-500/20',
          glow: 'shadow-red-400/50'
        };
      default:
        return { 
          icon: (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ), 
          color: 'text-cyber-gray-400',
          bg: 'bg-cyber-gray-500/20',
          glow: 'shadow-cyber-gray-400/50'
        };
    }
  };

  const formatUptime = (seconds) => {
    if (!seconds) return 'Unknown';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const getOverallStatus = () => {
    if (!health) return 'unknown';
    if (health.status === 'healthy' || health.status === 'up') return 'healthy';
    if (health.warnings && health.warnings.length > 0) return 'degraded';
    return health.status;
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
            overallStatus === 'unhealthy' ? 'bg-red-400' : 'bg-cyber-gray-400'
          }`}></div>
          System Health
        </h3>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`cyber-button p-2 rounded-lg text-xs transition-all duration-300 ${
              autoRefresh ? 'bg-neon-orange-500/20' : ''
            }`}
            title={autoRefresh ? 'Disable auto-refresh' : 'Enable auto-refresh'}
          >
            <svg className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
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
        </div>
      </div>

      {loading && !health ? (
        <div className="cyber-pulse">
          <div className="h-4 bg-neon-orange-500/20 rounded w-1/3 mb-3 animate-pulse"></div>
          <div className="space-y-2">
            <div className="h-3 bg-cyber-gray-600/30 rounded animate-pulse"></div>
            <div className="h-3 bg-cyber-gray-600/30 rounded w-3/4 animate-pulse"></div>
          </div>
        </div>
      ) : error ? (
        <div className="text-center py-6">
          <svg className="w-12 h-12 mx-auto mb-4 text-red-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.732 18.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={() => checkHealth(true)}
            className="cyber-button px-4 py-2 rounded-lg hover:scale-105 transform transition-all duration-300"
          >
            Retry Connection
          </button>
        </div>
      ) : health ? (
        <>
          {/* Main Status */}
          <div className={`glass rounded-xl p-4 border-cyber mb-4 ${statusInfo.glow}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-lg ${statusInfo.bg} ${statusInfo.color}`}>
                  {statusInfo.icon}
                </div>
                <div>
                  <h4 className="font-semibold text-white capitalize">{overallStatus}</h4>
                  <p className="text-xs cyber-subheading">
                    Last checked: {new Date(health.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setExpanded(!expanded)}
                className="cyber-button p-2 rounded-lg hover:scale-110 transform transition-all duration-300"
              >
                <svg className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="glass rounded-lg p-3 border-cyber">
              <div className="cyber-subheading text-xs mb-1">Version</div>
              <div className="text-white font-semibold font-mono text-sm">{health.version || 'Unknown'}</div>
            </div>
            <div className="glass rounded-lg p-3 border-cyber">
              <div className="cyber-subheading text-xs mb-1">Uptime</div>
              <div className="text-neon-orange-400 font-semibold text-sm">{formatUptime(health.uptime)}</div>
            </div>
          </div>

          {/* Warnings */}
          {health.warnings && health.warnings.length > 0 && (
            <div className="glass rounded-xl p-4 border-yellow-500/30 bg-yellow-500/10 mb-4">
              <h5 className="cyber-subheading mb-2 flex items-center">
                <svg className="w-4 h-4 mr-2 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.732 18.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                System Warnings
              </h5>
              <div className="space-y-1">
                {health.warnings.map((warning, index) => (
                  <p key={index} className="text-yellow-300 text-sm">• {warning}</p>
                ))}
              </div>
            </div>
          )}

          {/* Expanded Details */}
          {expanded && (
            <div className="space-y-4">
              {/* Services Status */}
              {health.services && Object.keys(health.services).length > 0 && (
                <div>
                  <h5 className="cyber-subheading mb-3 flex items-center">
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                    </svg>
                    Services
                  </h5>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {Object.entries(health.services).map(([service, status]) => {
                      const serviceStatus = getStatusIcon(typeof status === 'string' ? status : status.status);
                      return (
                        <div key={service} className="glass rounded-lg p-3 border-cyber">
                          <div className="flex items-center justify-between">
                            <span className="text-white text-sm font-medium">{service}</span>
                            <div className={`flex items-center space-x-1 ${serviceStatus.color}`}>
                              {serviceStatus.icon}
                              <span className="text-xs">
                                {typeof status === 'string' ? status : status.status}
                              </span>
                            </div>
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
                  <h5 className="cyber-subheading mb-3 flex items-center">
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                    </svg>
                    Database
                  </h5>
                  <div className="glass rounded-lg p-3 border-cyber">
                    <div className="flex items-center justify-between">
                      <span className="text-white text-sm font-medium">Connection</span>
                      <div className={`flex items-center space-x-1 ${getStatusIcon(health.database.status).color}`}>
                        {getStatusIcon(health.database.status).icon}
                        <span className="text-xs">{health.database.status}</span>
                      </div>
                    </div>
                    {health.database.connection_pool && (
                      <div className="mt-2 text-xs cyber-subheading">
                        Pool: {health.database.connection_pool.active || 0} active, {health.database.connection_pool.idle || 0} idle
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Performance Metrics */}
              {health.performance && Object.keys(health.performance).length > 0 && (
                <div>
                  <h5 className="cyber-subheading mb-3 flex items-center">
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                    Performance
                  </h5>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {Object.entries(health.performance).map(([metric, value]) => (
                      <div key={metric} className="glass rounded-lg p-3 border-cyber">
                        <div className="flex items-center justify-between">
                          <span className="text-white text-sm font-medium capitalize">{metric.replace('_', ' ')}</span>
                          <span className="text-neon-orange-400 text-sm font-semibold">
                            {typeof value === 'number' ? 
                              (metric.includes('time') ? `${value}ms` : value) : 
                              value
                            }
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Environment Info */}
              {health.environment && (
                <div>
                  <h5 className="cyber-subheading mb-3 flex items-center">
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    Environment
                  </h5>
                  <div className="glass rounded-lg p-3 border-cyber">
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-cyber-gray-300">Mode:</span>
                        <span className="text-white font-medium">{health.environment.mode || 'Unknown'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-cyber-gray-300">Debug:</span>
                        <span className={`font-medium ${health.environment.debug ? 'text-yellow-400' : 'text-green-400'}`}>
                          {health.environment.debug ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-6">
          <svg className="w-12 h-12 mx-auto mb-4 text-cyber-gray-500 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="cyber-subheading">System status unknown</p>
          <p className="text-sm mt-1 text-cyber-gray-400">Click refresh to check system health</p>
        </div>
      )}
    </div>
  );
};

export default HealthCheck;
