import React, { useState, useEffect } from 'react';
import { ChevronDownIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';

/**
 * Mode Selector Component - Production-grade mode selection UI
 * Implements blueprint-specified modes: conservative, balanced, exploratory, focused
 */
const ModeSelector = ({ 
  currentMode = 'balanced', 
  onModeChange, 
  disabled = false,
  showDescription = true,
  className = '' 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedMode, setSelectedMode] = useState(currentMode);

  // Blueprint-compliant mode configurations
  const modes = {
    conservative: {
      name: 'Conservative',
      description: 'Safe, predictable continuations with proven approaches',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      icon: '🛡️',
      temperature: 0.3,
      creativity: 0.2,
      consistency: 0.8
    },
    balanced: {
      name: 'Balanced',
      description: 'Balanced creativity and consistency for reliable results',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      icon: '⚖️',
      temperature: 0.5,
      creativity: 0.5,
      consistency: 0.5
    },
    exploratory: {
      name: 'Exploratory',
      description: 'Creative, experimental approaches with novel solutions',
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      borderColor: 'border-purple-200',
      icon: '🚀',
      temperature: 0.8,
      creativity: 0.8,
      consistency: 0.2
    },
    focused: {
      name: 'Focused',
      description: 'Highly specific, targeted outcomes with precision',
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
      borderColor: 'border-orange-200',
      icon: '🎯',
      temperature: 0.2,
      creativity: 0.1,
      consistency: 0.9
    }
  };

  const currentModeConfig = modes[selectedMode] || modes.balanced;

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
      <span className="w-16 text-gray-600">{label}:</span>
      <div className="flex-1 bg-gray-200 rounded-full h-2 ml-2">
        <div 
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${value * 100}%` }}
        />
      </div>
      <span className="ml-2 text-gray-500 w-8">{Math.round(value * 100)}%</span>
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
          w-full px-4 py-3 text-left border rounded-lg shadow-sm
          ${currentModeConfig.bgColor} ${currentModeConfig.borderColor}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-md'}
          transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500
        `}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-xl">{currentModeConfig.icon}</span>
            <div>
              <div className={`font-medium ${currentModeConfig.color}`}>
                {currentModeConfig.name} Mode
              </div>
              {showDescription && (
                <div className="text-sm text-gray-600 mt-1">
                  {currentModeConfig.description}
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Cog6ToothIcon className="h-4 w-4 text-gray-400" />
            <ChevronDownIcon 
              className={`h-4 w-4 text-gray-400 transition-transform duration-200 ${
                isOpen ? 'transform rotate-180' : ''
              }`} 
            />
          </div>
        </div>
      </button>

      {/* Mode Selection Dropdown */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg">
          <div className="py-2">
            {Object.entries(modes).map(([modeKey, mode]) => (
              <button
                key={modeKey}
                onClick={() => handleModeSelect(modeKey)}
                className={`
                  w-full px-4 py-3 text-left hover:bg-gray-50
                  ${selectedMode === modeKey ? mode.bgColor : ''}
                  transition-colors duration-150
                `}
              >
                <div className="flex items-start space-x-3">
                  <span className="text-xl">{mode.icon}</span>
                  <div className="flex-1">
                    <div className={`font-medium ${mode.color}`}>
                      {mode.name}
                    </div>
                    <div className="text-sm text-gray-600 mt-1">
                      {mode.description}
                    </div>
                    
                    {/* Mode Metrics */}
                    <div className="mt-3 space-y-1">
                      <MetricBar 
                        label="Creative" 
                        value={mode.creativity} 
                        color="bg-purple-400" 
                      />
                      <MetricBar 
                        label="Consistent" 
                        value={mode.consistency} 
                        color="bg-blue-400" 
                      />
                      <div className="flex items-center text-xs">
                        <span className="w-16 text-gray-600">Temp:</span>
                        <span className="ml-2 text-gray-500">{mode.temperature}</span>
                      </div>
                    </div>
                  </div>
                  
                  {selectedMode === modeKey && (
                    <div className="flex-shrink-0">
                      <div className={`w-3 h-3 rounded-full ${mode.color.replace('text-', 'bg-')}`} />
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Click away listener */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
};

export default ModeSelector;
