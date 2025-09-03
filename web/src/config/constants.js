// Frontend configuration constants
// Matches backend constants for production-grade consistency

export const BACKEND_PORT = 8000;
export const FRONTEND_PORT = 3000;

export const API_CONFIG = {
  BASE_URL: `http://localhost:${BACKEND_PORT}`,
  ENDPOINTS: {
    SESSION: '/api/session',
    PTG: '/api/ptg',
    AGENTS: '/api/agents',
    AUTH: '/api/auth',
  },
  TIMEOUT: 30000, // 30 seconds
};

export const OAUTH_CONFIG = {
  GOOGLE_CLIENT_ID: process.env.REACT_APP_GOOGLE_CLIENT_ID || '',
  REDIRECT_URI: `http://localhost:${FRONTEND_PORT}/auth/callback`,
};

export const AI_MODES = {
  CONSERVATIVE: 'conservative',
  BALANCED: 'balanced', 
  EXPLORATORY: 'exploratory',
  FOCUSED: 'focused',
  CREATIVE: 'creative', // Enhanced for story mode
};

export const DEFAULT_MODE = AI_MODES.BALANCED;

export const AGENT_TYPES = {
  GENERAL: 'general',
  CREATIVE: 'creative',
  ANALYTICAL: 'analytical',
  TECHNICAL: 'technical',
  RESEARCH: 'research',
  WRITING: 'writing',
};

// Topic domains supported by the enhanced system
export const TOPIC_DOMAINS = {
  STORY: 'story',
  EDUCATION: 'education',
  RESEARCH: 'research',
  PRODUCT: 'product',
  MARKETING: 'marketing',
  HEALTHCARE: 'healthcare_nonclinical',
  LEGAL: 'legal_plain',
  ENGINEERING: 'engineering',
  DATA_SCIENCE: 'data_science',
  PRODUCTIVITY: 'personal_productivity',
  ACCESSIBILITY: 'accessibility',
  TRAINING: 'teaching_training',
};

export const DOMAIN_CONFIGS = {
  [TOPIC_DOMAINS.STORY]: {
    name: 'Creative Writing',
    description: 'Stories, narratives, and creative content',
    icon: '📚',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    preferredMode: AI_MODES.CREATIVE,
    examples: ['Write a story about...', 'Continue this narrative...', 'Develop a character...']
  },
  [TOPIC_DOMAINS.EDUCATION]: {
    name: 'Education',
    description: 'Lesson plans, curricula, and learning materials',
    icon: '🎓',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    preferredMode: AI_MODES.BALANCED,
    examples: ['Create a lesson plan for...', 'Design a study guide...', 'Develop a quiz...']
  },
  [TOPIC_DOMAINS.RESEARCH]: {
    name: 'Research',
    description: 'Methodologies, experiments, and analysis plans',
    icon: '🔬',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    preferredMode: AI_MODES.CONSERVATIVE,
    examples: ['Design an experiment...', 'Create a methodology...', 'Plan data analysis...']
  },
  [TOPIC_DOMAINS.PRODUCT]: {
    name: 'Product Development',
    description: 'Product requirements, user stories, and features',
    icon: '📱',
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50',
    borderColor: 'border-indigo-200',
    preferredMode: AI_MODES.FOCUSED,
    examples: ['Write user stories for...', 'Create a PRD...', 'Define requirements...']
  },
  [TOPIC_DOMAINS.MARKETING]: {
    name: 'Marketing',
    description: 'Campaigns, strategies, and audience analysis',
    icon: '📢',
    color: 'text-pink-600',
    bgColor: 'bg-pink-50',
    borderColor: 'border-pink-200',
    preferredMode: AI_MODES.EXPLORATORY,
    examples: ['Plan a campaign for...', 'Create marketing strategy...', 'Analyze audience...']
  },
  [TOPIC_DOMAINS.HEALTHCARE]: {
    name: 'Health & Wellness',
    description: 'Wellness guides and health education (non-clinical)',
    icon: '🏥',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    preferredMode: AI_MODES.CONSERVATIVE,
    examples: ['Create wellness guide...', 'Plan fitness routine...', 'Stress management...']
  },
  [TOPIC_DOMAINS.LEGAL]: {
    name: 'Legal Education',
    description: 'Legal concepts and policy explanation (education only)',
    icon: '⚖️',
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
    preferredMode: AI_MODES.CONSERVATIVE,
    examples: ['Explain this policy...', 'Summarize rights...', 'Define legal terms...']
  },
  [TOPIC_DOMAINS.ENGINEERING]: {
    name: 'Engineering',
    description: 'System design, architecture, and technical specs',
    icon: '⚙️',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    preferredMode: AI_MODES.FOCUSED,
    examples: ['Design system architecture...', 'Create technical spec...', 'Plan infrastructure...']
  },
  [TOPIC_DOMAINS.DATA_SCIENCE]: {
    name: 'Data Science',
    description: 'Analysis plans, models, and data visualization',
    icon: '📊',
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-50',
    borderColor: 'border-cyan-200',
    preferredMode: AI_MODES.BALANCED,
    examples: ['Plan data analysis...', 'Design ML model...', 'Create visualization...']
  },
  [TOPIC_DOMAINS.PRODUCTIVITY]: {
    name: 'Productivity',
    description: 'Study plans, habits, and time management',
    icon: '⏰',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    preferredMode: AI_MODES.FOCUSED,
    examples: ['Create study plan...', 'Design habit tracker...', 'Plan schedule...']
  },
  [TOPIC_DOMAINS.ACCESSIBILITY]: {
    name: 'Accessibility',
    description: 'Inclusive design and accessibility compliance',
    icon: '♿',
    color: 'text-violet-600',
    bgColor: 'bg-violet-50',
    borderColor: 'border-violet-200',
    preferredMode: AI_MODES.CONSERVATIVE,
    examples: ['Audit accessibility...', 'Design inclusive UI...', 'Check WCAG compliance...']
  },
  [TOPIC_DOMAINS.TRAINING]: {
    name: 'Training & Development',
    description: 'Workshops, skills development, and coaching',
    icon: '🎯',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    preferredMode: AI_MODES.BALANCED,
    examples: ['Design workshop...', 'Create training plan...', 'Develop curriculum...']
  }
};

export const UI_CONFIG = {
  TOAST_DURATION: 3000,
  ANIMATION_DURATION: 200,
  DEBOUNCE_DELAY: 300,
};

export const DEFAULT_DOMAIN = TOPIC_DOMAINS.STORY;
