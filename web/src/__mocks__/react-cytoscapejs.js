import React from 'react';
// Simple mock for CytoscapeComponent for Jest
const CytoscapeComponent = typeof jest !== 'undefined' ? jest.fn(() => <div data-testid="cytoscape-mock" />) : () => <div data-testid="cytoscape-mock" />;
export default CytoscapeComponent;
