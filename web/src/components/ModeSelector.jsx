import React, { useState, useEffect } from 'react';

/**
 * PRODUCTION-GRADE Mode Selector with smart recommendations
 * Implements blueprint-specified modes: conservative, balanced, exploratory, focused, creative
 */
const ModeSelector = ({ 
  currentMode = 'balanced', 
  onModeChange, 
  disabled = false,
  currentDomain = null,  // Pass domain for smart mode suggestions
  className = '' 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedMode, setSelectedMode] = useState(currentMode);

  // Blueprint-compliant mode configurations with cyber styling
  const modes = {
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
    },
    creative: {
      name: 'Creative',
      description: 'Maximum creativity for stories and artistic content',
      color: 'text-pink-400',
      bgColor: 'bg-pink-500/10',
      borderColor: 'border-pink-500/30',
      icon: '🎨',
      temperature: 0.9,
      creativity: 0.9,
      consistency: 0.1
    }
  };

  const currentModeConfig = modes[selectedMode] || modes.balanced;

  // Smart mode recommendation based on domain
  const getRecommendedMode = () => {
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
  };

  const recommendedMode = getRecommendedMode();

  useEffect(() => {
    setSelectedMode(currentMode);
  }, [currentMode]);

  const handleModeSelect = (mode) => {
    setSelectedMode(mode);
    setIsOpen(false);
    if (onModeChange) {
      onModeChange(mode, modes[mode]);
    }
  };

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
