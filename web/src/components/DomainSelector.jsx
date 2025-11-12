import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { fetchWithAuth } from '../utils/api';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

/**
 * PRODUCTION-GRADE Domain Selector with AI-powered detection
 * Uses PerceptionAgent to intelligently detect content domain
 */
const DomainSelector = ({ 
  currentDomain = 'story', 
  onDomainChange, 
  disabled = false,
  userInput = '',  // Current text content for AI detection
  autoDetect = true,  // Enable AI-powered detection
  className = '' 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedDomain, setSelectedDomain] = useState(currentDomain);
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectionResult, setDetectionResult] = useState(null);

  // Domain configurations matching backend TOPIC_DOMAINS (memoized to prevent re-creation)
  const domains = useMemo(() => ({
    story: {
      name: 'Creative Writing',
      description: 'Stories, narratives, and creative content',
      icon: '📖',
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
      borderColor: 'border-purple-500/30',
      preferredMode: 'creative'
    },
    screenplay: {
      name: 'Screenplay',
      description: 'Movie scripts, dialogues, and scene descriptions',
      icon: '🎬',
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/30',
      preferredMode: 'balanced'
    },
    technical: {
      name: 'Technical Writing',
      description: 'Documentation, manuals, and technical content',
      icon: '⚙️',
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10',
      borderColor: 'border-cyan-500/30',
      preferredMode: 'focused'
    },
    academic: {
      name: 'Academic',
      description: 'Research papers, essays, and scholarly content',
      icon: '🎓',
      color: 'text-green-400',
      bgColor: 'bg-green-500/10',
      borderColor: 'border-green-500/30',
      preferredMode: 'conservative'
    },
    business: {
      name: 'Business',
      description: 'Reports, proposals, and professional documents',
      icon: '💼',
      color: 'text-orange-400',
      bgColor: 'bg-orange-500/10',
      borderColor: 'border-orange-500/30',
      preferredMode: 'balanced'
    },
    marketing: {
      name: 'Marketing',
      description: 'Ads, copy, and promotional content',
      icon: '📢',
      color: 'text-pink-400',
      bgColor: 'bg-pink-500/10',
      borderColor: 'border-pink-500/30',
      preferredMode: 'exploratory'
    }
  }), []); // Empty dependency array since this config never changes

  const currentConfig = domains[selectedDomain] || domains.story;

  useEffect(() => {
    setSelectedDomain(currentDomain);
  }, [currentDomain]);

  // Memoized domain selection handler to avoid infinite re-renders
  const handleDomainSelect = useCallback((domain, isAIDetected = false) => {
    setSelectedDomain(domain);
    setIsOpen(false);
    
    if (onDomainChange) {
      onDomainChange(domain, {
        ...domains[domain],
        isAIDetected,
        confidence: detectionResult?.confidence
      });
    }
  }, [onDomainChange, detectionResult, domains]);

  // AI-powered domain detection using PerceptionAgent (debounced)
  useEffect(() => {
    if (!autoDetect || !userInput || userInput.trim().length < 20) return;

    let mounted = true;
    const timeout = setTimeout(() => {
      const detectDomain = async () => {
        if (!mounted) return;
        setIsDetecting(true);
        try {
          const response = await fetchWithAuth(`${API_BASE_URL}/api/perception/detect-domain`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: userInput })
          });

          if (!mounted) return;
          if (response.ok) {
            const result = await response.json();
            if (!mounted) return;
            setDetectionResult(result);

            // Auto-select detected domain if confidence is high
            if (result.domain && result.confidence > 0.6 && autoDetect) {
              handleDomainSelect(result.domain, true);
            }
          }
        } catch (error) {
          if (mounted) console.error('Domain detection failed:', error);
        } finally {
          if (mounted) setIsDetecting(false);
        }
      };

      detectDomain();
    }, 2000); // Wait 2 seconds after user stops typing

    return () => {
      mounted = false;
      clearTimeout(timeout);
    };
  }, [userInput, autoDetect, handleDomainSelect]);

  return (
    <div className={`relative ${className}`}>
      {/* Domain Selector Button */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        className={`
          w-full px-4 py-3 text-left border rounded-lg
          ${currentConfig.bgColor} ${currentConfig.borderColor}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-md glass'}
          transition-all duration-200
        `}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">{currentConfig.icon}</span>
            <div>
              <div className={`font-medium ${currentConfig.color}`}>
                {currentConfig.name}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {currentConfig.description}
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {isDetecting && (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-400"></div>
            )}
            {detectionResult && detectionResult.confidence > 0.6 && (
              <div className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">
                AI: {Math.round(detectionResult.confidence * 100)}%
              </div>
            )}
            <svg 
              className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute z-50 w-full mt-2 glass-strong border-cyber rounded-lg shadow-lg max-h-96 overflow-y-auto">
            <div className="py-2">
              <div className="px-3 py-2 text-xs font-semibold text-gray-400 border-b border-gray-700">
                Select Content Domain {autoDetect && '(AI-Powered)'}
              </div>
              {Object.entries(domains).map(([key, domain]) => (
                <button
                  key={key}
                  onClick={() => handleDomainSelect(key)}
                  className={`
                    w-full px-4 py-3 text-left hover:bg-gray-800/50
                    ${selectedDomain === key ? domain.bgColor + ' ' + domain.borderColor + ' border-l-4' : ''}
                    transition-colors duration-150
                  `}
                >
                  <div className="flex items-start space-x-3">
                    <span className="text-2xl">{domain.icon}</span>
                    <div className="flex-1">
                      <div className={`font-medium ${domain.color}`}>
                        {domain.name}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {domain.description}
                      </div>
                      <div className="mt-2 flex items-center space-x-2">
                        <span className="text-xs text-gray-500">Recommended mode:</span>
                        <span className="text-xs px-2 py-1 bg-gray-700 text-gray-300 rounded-full">
                          {domain.preferredMode}
                        </span>
                      </div>
                    </div>
                    {selectedDomain === key && (
                      <svg className="w-5 h-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                </button>
              ))}
            </div>
            
            {/* AI Detection Info */}
            {detectionResult && (
              <div className="px-4 py-3 bg-gray-900/50 border-t border-gray-700">
                <div className="text-xs text-gray-400 mb-1">
                  ✨ AI detected: <span className="text-purple-400 font-medium">{detectionResult.domain}</span>
                </div>
                <div className="text-xs text-gray-500">
                  Confidence: {Math.round(detectionResult.confidence * 100)}%
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default DomainSelector;
