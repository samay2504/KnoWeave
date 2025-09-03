import React, { useState, useEffect } from 'react';
import { ChevronDownIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';
import { TOPIC_DOMAINS, DOMAIN_CONFIGS, DEFAULT_DOMAIN } from '../config/constants';

/**
 * Domain Selector Component - Multi-domain selection UI
 * Supports the enhanced topic-agnostic Human-AI Co-Creation system
 */
const DomainSelector = ({ 
  currentDomain = DEFAULT_DOMAIN, 
  onDomainChange, 
  disabled = false,
  showDescription = true,
  showExamples = false,
  className = '' 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedDomain, setSelectedDomain] = useState(currentDomain);

  const currentDomainConfig = DOMAIN_CONFIGS[selectedDomain] || DOMAIN_CONFIGS[DEFAULT_DOMAIN];

  useEffect(() => {
    setSelectedDomain(currentDomain);
  }, [currentDomain]);

  const handleDomainSelect = (domain) => {
    setSelectedDomain(domain);
    setIsOpen(false);
    if (onDomainChange) {
      onDomainChange(domain, DOMAIN_CONFIGS[domain]);
    }
  };

  return (
    <div className={`relative ${className}`}>
      {/* Domain Selector Button */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        className={`
          w-full px-4 py-3 text-left border rounded-lg shadow-sm
          ${currentDomainConfig.bgColor} ${currentDomainConfig.borderColor}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-md'}
          transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500
        `}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-xl">{currentDomainConfig.icon}</span>
            <div>
              <div className={`font-medium ${currentDomainConfig.color}`}>
                {currentDomainConfig.name}
              </div>
              {showDescription && (
                <div className="text-sm text-gray-600 mt-1">
                  {currentDomainConfig.description}
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
              {Object.keys(TOPIC_DOMAINS).length} domains
            </span>
            <ChevronDownIcon 
              className={`h-4 w-4 text-gray-400 transition-transform duration-200 ${
                isOpen ? 'transform rotate-180' : ''
              }`} 
            />
          </div>
        </div>
      </button>

      {/* Domain Selection Dropdown */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-y-auto">
          <div className="py-2">
            <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider border-b">
              Select Content Domain
            </div>
            {Object.entries(DOMAIN_CONFIGS).map(([domainKey, domain]) => (
              <button
                key={domainKey}
                onClick={() => handleDomainSelect(domainKey)}
                className={`
                  w-full px-4 py-3 text-left hover:bg-gray-50
                  ${selectedDomain === domainKey ? domain.bgColor : ''}
                  transition-colors duration-150 border-b border-gray-100 last:border-b-0
                `}
              >
                <div className="flex items-start space-x-3">
                  <span className="text-xl">{domain.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className={`font-medium ${domain.color}`}>
                      {domain.name}
                    </div>
                    <div className="text-sm text-gray-600 mt-1">
                      {domain.description}
                    </div>
                    {showExamples && domain.examples && (
                      <div className="mt-2">
                        <div className="text-xs text-gray-500 mb-1">Examples:</div>
                        <div className="space-y-1">
                          {domain.examples.slice(0, 2).map((example, idx) => (
                            <div key={idx} className="text-xs text-gray-600 bg-gray-50 px-2 py-1 rounded italic">
                              "{example}"
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="mt-2 flex items-center space-x-2">
                      <span className="text-xs text-gray-500">Preferred mode:</span>
                      <span className="text-xs font-medium text-blue-600 bg-blue-100 px-2 py-1 rounded-full">
                        {domain.preferredMode}
                      </span>
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
          
          {/* Domain Stats Footer */}
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
            <div className="text-xs text-gray-600">
              ✨ Topic-agnostic AI system supports {Object.keys(DOMAIN_CONFIGS).length} domains
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Each domain has specialized validation and examples
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DomainSelector;
