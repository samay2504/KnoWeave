import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { fetchWithAuth } from '../utils/api';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

/**
 * PRODUCTION-GRADE Mode Selector with AI-powered LLM recommendations
 * Uses PerceptionAgent to intelligently recommend modes based on content analysis
 */
const ModeSelector = ({ 
  currentMode = 'balanced', 
  onModeChange, 
  disabled = false,
  currentDomain = null,
  userInput = '',  // Current text content for AI analysis
  autoDetect = true,  // Enable AI-powered mode recommendations
  className = '' 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedMode, setSelectedMode] = useState(currentMode);
  const [isDetecting, setIsDetecting] = useState(false);
  const [aiRecommendation, setAiRecommendation] = useState(null);
  const [lastDetectedContent, setLastDetectedContent] = useState('');
  const [lastDetectedDomain, setLastDetectedDomain] = useState('');

  // Blueprint-compliant mode configurations with cyber styling (memoized)
  const modes = useMemo(() => ({
    conservative: {
      name: 'Conservative',
      description: 'Safe, predictable continuations with proven approaches',
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/30',
      icon: '🛡️',
      temperature: 0.3,
      creativity: 0.2,
      consistency: 0.8
    },
    balanced: {
      name: 'Balanced Mode',
      description: 'Balanced creativity and consistency for reliable results',
      color: 'text-green-400',
      bgColor: 'bg-green-500/10',
      borderColor: 'border-green-500/30',
      icon: '⚖️',
      temperature: 0.5,
      creativity: 0.5,
      consistency: 0.5
    },
    exploratory: {
      name: 'Exploratory',
      description: 'Creative, experimental approaches with novel solutions',
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
      borderColor: 'border-purple-500/30',
      icon: '🚀',
      temperature: 0.8,
      creativity: 0.8,
      consistency: 0.2
    },
    focused: {
      name: 'Focused',
      description: 'Highly specific, targeted outcomes with precision',
      color: 'text-orange-400',
      bgColor: 'bg-orange-500/10',
      borderColor: 'border-orange-500/30',
      icon: '🎯',
      temperature: 0.2,
      creativity: 0.1,
      consistency: 0.9
    }
  }), []);

  const currentModeConfig = modes[selectedMode] || modes.balanced;

  // Static rule-based recommendation based on domain (fallback)
  const getStaticRecommendation = useCallback(() => {
    if (!currentDomain) return null;
    
    const recommendations = {
      story: 'creative',
      screenplay: 'balanced',
      technical: 'focused',
      academic: 'conservative',
      business: 'balanced',
      marketing: 'exploratory'
    };
    
    return recommendations[currentDomain];
  }, [currentDomain]);

  // Use AI recommendation if available, fallback to static
  const recommendedMode = aiRecommendation?.recommended_mode || getStaticRecommendation();

  useEffect(() => {
    setSelectedMode(currentMode);
  }, [currentMode]);

  // Memoized mode selection handler
  const handleModeSelect = useCallback((mode, isAIRecommended = false) => {
    setSelectedMode(mode);
    setIsOpen(false);
    if (onModeChange) {
      onModeChange(mode, {
        ...modes[mode],
        isAIRecommended,
        confidence: aiRecommendation?.confidence,
        reasoning: aiRecommendation?.reasoning
      });
    }
  }, [onModeChange, modes, aiRecommendation]);

  // AI-powered mode recommendation using PerceptionAgent (debounced)
  useEffect(() => {
    if (!autoDetect || !userInput || userInput.trim().length < 20) return;
    
    // PRODUCTION FIX: Skip if content and domain haven't changed
    const normalizedInput = userInput.trim().toLowerCase();
    const normalizedLast = lastDetectedContent.trim().toLowerCase();
    if (normalizedInput === normalizedLast && currentDomain === lastDetectedDomain) {
      return;
    }

    let mounted = true;
    const timeout = setTimeout(() => {
      const detectMode = async () => {
        if (!mounted) return;
        setIsDetecting(true);
        try {
          const response = await fetchWithAuth(`${API_BASE_URL}/api/agents/perception/recommend-mode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              text: userInput,
              domain: currentDomain 
            })
          });

          if (!mounted) return;
          if (response.ok) {
            const data = await response.json();
            if (!mounted) return;
            
            const recommendation = data.mode_recommendation || data;
            setAiRecommendation(recommendation);
            setLastDetectedContent(userInput);
            setLastDetectedDomain(currentDomain);

            // Auto-select recommended mode if confidence is high
            if (recommendation.recommended_mode && recommendation.confidence > 0.7 && autoDetect) {
              handleModeSelect(recommendation.recommended_mode, true);
            }
          }
        } catch (error) {
          if (mounted) console.error('Mode recommendation failed:', error);
        } finally {
          if (mounted) setIsDetecting(false);
        }
      };

      detectMode();
    }, 2000); // Wait 2 seconds after user stops typing

    return () => {
      mounted = false;
      clearTimeout(timeout);
    };
  }, [userInput, currentDomain, autoDetect, handleModeSelect, lastDetectedContent, lastDetectedDomain]);

  const MetricBar = ({ label, value, color }) => (
    <div className="flex items-center text-xs">
      <span className="w-20 text-gray-400">{label}:</span>
      <div className="flex-1 bg-gray-800 rounded-full h-2 ml-2">
        <div 
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${value * 100}%` }}
        />
      </div>
      <span className="ml-2 text-gray-500 w-10 text-right">{Math.round(value * 100)}%</span>
    </div>
  );

  return (
    <div className={`relative ${className}`}>
      {/* Mode Selector Button */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        className={`
          w-full px-4 py-3 text-left border rounded-lg glass
          ${currentModeConfig.bgColor} ${currentModeConfig.borderColor}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-md'}
          transition-all duration-200
        `}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">{currentModeConfig.icon}</span>
            <div>
              <div className={`font-medium ${currentModeConfig.color}`}>
                {currentModeConfig.name}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {currentModeConfig.description}
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {isDetecting && (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-400"></div>
            )}
            {aiRecommendation && aiRecommendation.confidence > 0.7 && (
              <div className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">
                AI: {Math.round(aiRecommendation.confidence * 100)}%
              </div>
            )}
            {recommendedMode === selectedMode && (
              <div className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">
                ✨ Recommended
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

      {/* Mode Selection Dropdown */}
      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute z-50 w-full mt-2 glass-strong border-cyber rounded-lg shadow-lg">
            <div className="py-2">
              <div className="px-3 py-2 text-xs font-semibold text-gray-400 border-b border-gray-700">
                Select AI Mode
              </div>
              {Object.entries(modes).map(([modeKey, mode]) => (
                <button
                  key={modeKey}
                  onClick={() => handleModeSelect(modeKey)}
                  className={`
                    w-full px-4 py-3 text-left hover:bg-gray-800/50
                    ${selectedMode === modeKey ? mode.bgColor + ' ' + mode.borderColor + ' border-l-4' : ''}
                    transition-colors duration-150
                  `}
                >
                  <div className="flex items-start space-x-3">
                    <span className="text-2xl">{mode.icon}</span>
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className={`font-medium ${mode.color}`}>
                          {mode.name}
                        </span>
                        {recommendedMode === modeKey && (
                          <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">
                            ✨ Recommended
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {mode.description}
                      </div>
                      
                      {/* Mode Metrics */}
                      <div className="mt-3 space-y-1">
                        <MetricBar 
                          label="Creative" 
                          value={mode.creativity} 
                          color="bg-purple-500" 
                        />
                        <MetricBar 
                          label="Consistent" 
                          value={mode.consistency} 
                          color="bg-blue-500" 
                        />
                        <div className="flex items-center text-xs">
                          <span className="w-20 text-gray-400">Temp:</span>
                          <span className="ml-2 text-gray-300">{mode.temperature}</span>
                        </div>
                      </div>
                    </div>
                    
                    {selectedMode === modeKey && (
                      <svg className="w-5 h-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ModeSelector;
