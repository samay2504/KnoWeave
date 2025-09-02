// ArangoDB initialization script for Human-AI Co-Creation Platform
// This script creates all required databases, collections, graphs, and indexes
// It is idempotent and safe to run multiple times

const db = require('@arangodb').db;
const graph_module = require('@arangodb/general-graph');

const DATABASE_NAME = 'human_ai_co_create';
const GRAPH_NAME = 'knowledge_graph';

// Database creation (if not exists)
try {
    if (!db._databases().includes(DATABASE_NAME)) {
        db._createDatabase(DATABASE_NAME);
        print(`Created database: ${DATABASE_NAME}`);
    } else {
        print(`Database already exists: ${DATABASE_NAME}`);
    }
} catch (e) {
    print(`Database creation error: ${e.message}`);
}

// Switch to application database
db._useDatabase(DATABASE_NAME);

// Collection definitions with schema validation
const collections = [
    {
        name: 'users',
        type: 'document',
        schema: {
            rule: {
                type: 'object',
                properties: {
                    google_id: { type: 'string' },
                    email: { type: 'string', format: 'email' },
                    name: { type: 'string', minLength: 1 },
                    picture: { type: 'string' },
                    created_at: { type: 'string', format: 'date-time' },
                    last_login: { type: 'string', format: 'date-time' },
                    preferences: { type: 'object' }
                },
                required: ['google_id', 'email', 'name'],
                additionalProperties: false
            },
            level: 'moderate',
            message: 'User document validation failed'
        }
    },
    {
        name: 'sessions',
        type: 'document',
        schema: {
            rule: {
                type: 'object',
                properties: {
                    user_id: { type: 'string' },
                    title: { type: 'string' },
                    topic: { type: 'string', enum: ['story', 'lesson_plan', 'guide', 'essay', 'other'] },
                    topic_descriptor: { type: 'object' },
                    content: { type: 'object' },
                    mode: { type: 'string', enum: ['balanced', 'creative', 'analytical', 'conservative'] },
                    workspace: { type: 'object' },
                    created_at: { type: 'string', format: 'date-time' },
                    updated_at: { type: 'string', format: 'date-time' },
                    tags: { type: 'array', items: { type: 'string' } },
                    status: { type: 'string', enum: ['active', 'archived', 'deleted'] }
                },
                required: ['user_id', 'topic', 'content', 'created_at'],
                additionalProperties: true
            },
            level: 'moderate'
        }
    },
    {
        name: 'entities',
        type: 'document',
        schema: {
            rule: {
                type: 'object',
                properties: {
                    session_id: { type: 'string' },
                    name: { type: 'string', minLength: 1 },
                    type: { type: 'string', enum: ['character', 'location', 'object', 'concept', 'event'] },
                    attributes: { type: 'object' },
                    importance_score: { type: 'number', minimum: 0, maximum: 1 },
                    embedding: { type: 'array', items: { type: 'number' } },
                    created_at: { type: 'string', format: 'date-time' },
                    updated_at: { type: 'string', format: 'date-time' }
                },
                required: ['session_id', 'name', 'type'],
                additionalProperties: false
            },
            level: 'moderate'
        }
    },
    {
        name: 'events',
        type: 'document',
        schema: {
            rule: {
                type: 'object',
                properties: {
                    session_id: { type: 'string' },
                    summary: { type: 'string', minLength: 1 },
                    tokens_span: { type: 'object' },
                    embedding: { type: 'array', items: { type: 'number' } },
                    timestamp: { type: 'string', format: 'date-time' },
                    confidence: { type: 'number', minimum: 0, maximum: 1 },
                    parents: { type: 'array', items: { type: 'string' } },
                    importance_score: { type: 'number', minimum: 0, maximum: 1 },
                    created_at: { type: 'string', format: 'date-time' }
                },
                required: ['session_id', 'summary'],
                additionalProperties: false
            },
            level: 'moderate'
        }
    },
    {
        name: 'suggestions',
        type: 'document',
        schema: {
            rule: {
                type: 'object',
                properties: {
                    session_id: { type: 'string' },
                    user_id: { type: 'string' },
                    branches: { type: 'array', maxItems: 3 },
                    trigger_context: { type: 'object' },
                    acceptability_scores: { type: 'object' },
                    created_at: { type: 'string', format: 'date-time' },
                    accepted_branch: { type: 'string' },
                    feedback: { type: 'object' }
                },
                required: ['session_id', 'user_id', 'branches'],
                additionalProperties: false
            },
            level: 'moderate'
        }
    }
];

// Edge collections for the knowledge graph
const edgeCollections = [
    {
        name: 'relationships',
        type: 'edge',
        schema: {
            rule: {
                type: 'object',
                properties: {
                    _from: { type: 'string' },
                    _to: { type: 'string' },
                    session_id: { type: 'string' },
                    relationship_type: { 
                        type: 'string', 
                        enum: ['causal', 'temporal', 'co_ref', 'attribute', 'involves', 'located_in', 'part_of'] 
                    },
                    strength: { type: 'number', minimum: 0, maximum: 1 },
                    metadata: { type: 'object' },
                    created_at: { type: 'string', format: 'date-time' }
                },
                required: ['_from', '_to', 'session_id', 'relationship_type'],
                additionalProperties: false
            },
            level: 'moderate'
        }
    }
];

// Create document collections
collections.forEach(colDef => {
    try {
        if (!db._collection(colDef.name)) {
            const collection = db._createDocumentCollection(colDef.name);
            
            // Apply schema validation
            if (colDef.schema) {
                collection.properties({ schema: colDef.schema });
                print(`Created collection with schema validation: ${colDef.name}`);
            } else {
                print(`Created collection: ${colDef.name}`);
            }
        } else {
            print(`Collection already exists: ${colDef.name}`);
        }
    } catch (e) {
        print(`Error creating collection ${colDef.name}: ${e.message}`);
    }
});

// Create edge collections
edgeCollections.forEach(edgeDef => {
    try {
        if (!db._collection(edgeDef.name)) {
            const collection = db._createEdgeCollection(edgeDef.name);
            
            // Apply schema validation
            if (edgeDef.schema) {
                collection.properties({ schema: edgeDef.schema });
                print(`Created edge collection with schema validation: ${edgeDef.name}`);
            } else {
                print(`Created edge collection: ${edgeDef.name}`);
            }
        } else {
            print(`Edge collection already exists: ${edgeDef.name}`);
        }
    } catch (e) {
        print(`Error creating edge collection ${edgeDef.name}: ${e.message}`);
    }
});

// Create knowledge graph
try {
    if (!graph_module._exists(GRAPH_NAME)) {
        const graphDef = graph_module._create(GRAPH_NAME, [
            graph_module._relation('relationships', ['entities', 'events'], ['entities', 'events'])
        ]);
        print(`Created knowledge graph: ${GRAPH_NAME}`);
    } else {
        print(`Knowledge graph already exists: ${GRAPH_NAME}`);
    }
} catch (e) {
    print(`Error creating knowledge graph: ${e.message}`);
}

// Create indexes for performance optimization
const indexes = [
    // Users collection indexes
    { collection: 'users', fields: ['google_id'], unique: true },
    { collection: 'users', fields: ['email'], unique: true },
    { collection: 'users', fields: ['created_at'] },
    
    // Sessions collection indexes
    { collection: 'sessions', fields: ['user_id'] },
    { collection: 'sessions', fields: ['topic'] },
    { collection: 'sessions', fields: ['status'] },
    { collection: 'sessions', fields: ['created_at'] },
    { collection: 'sessions', fields: ['updated_at'] },
    { collection: 'sessions', fields: ['user_id', 'status'] },
    
    // Entities collection indexes
    { collection: 'entities', fields: ['session_id'] },
    { collection: 'entities', fields: ['type'] },
    { collection: 'entities', fields: ['importance_score'] },
    { collection: 'entities', fields: ['session_id', 'type'] },
    { collection: 'entities', fields: ['session_id', 'importance_score'] },
    
    // Events collection indexes
    { collection: 'events', fields: ['session_id'] },
    { collection: 'events', fields: ['timestamp'] },
    { collection: 'events', fields: ['importance_score'] },
    { collection: 'events', fields: ['session_id', 'timestamp'] },
    
    // Suggestions collection indexes
    { collection: 'suggestions', fields: ['session_id'] },
    { collection: 'suggestions', fields: ['user_id'] },
    { collection: 'suggestions', fields: ['created_at'] },
    { collection: 'suggestions', fields: ['session_id', 'created_at'] },
    
    // Relationships collection indexes
    { collection: 'relationships', fields: ['session_id'] },
    { collection: 'relationships', fields: ['relationship_type'] },
    { collection: 'relationships', fields: ['strength'] },
    { collection: 'relationships', fields: ['session_id', 'relationship_type'] }
];

indexes.forEach(indexDef => {
    try {
        const collection = db._collection(indexDef.collection);
        if (collection) {
            const indexOptions = indexDef.unique ? { unique: true } : {};
            collection.ensureIndex({ 
                type: 'persistent', 
                fields: indexDef.fields,
                ...indexOptions
            });
            print(`Created index on ${indexDef.collection}: [${indexDef.fields.join(', ')}]${indexDef.unique ? ' (unique)' : ''}`);
        }
    } catch (e) {
        print(`Error creating index on ${indexDef.collection}: ${e.message}`);
    }
});

// Create example development user (only in development mode)
if (process.env.NODE_ENV === 'development' || process.env.ARANGO_ENV === 'development') {
    try {
        const usersCollection = db._collection('users');
        const existingDevUser = usersCollection.firstExample({ google_id: 'dev_user_123' });
        
        if (!existingDevUser) {
            const devUser = {
                google_id: 'dev_user_123',
                email: 'dev@example.com',
                name: 'Development User',
                picture: 'https://via.placeholder.com/100',
                created_at: new Date().toISOString(),
                last_login: new Date().toISOString(),
                preferences: {
                    theme: 'dark',
                    ai_mode: 'balanced',
                    suggestion_policy: 'on_demand'
                }
            };
            
            usersCollection.save(devUser);
            print('Created development user');
        } else {
            print('Development user already exists');
        }
    } catch (e) {
        print(`Error creating development user: ${e.message}`);
    }
}

// Create application user with restricted permissions
try {
    const users = require('@arangodb/users');
    const appUser = 'app_user';
    const appPassword = process.env.ARANGO_APP_PASSWORD || 'change_me_in_production';
    
    if (!users.exists(appUser)) {
        users.save(appUser, appPassword);
        users.grantDatabase(appUser, DATABASE_NAME, 'rw');
        print(`Created application user: ${appUser}`);
    } else {
        print(`Application user already exists: ${appUser}`);
    }
} catch (e) {
    print(`Error managing application user: ${e.message}`);
}

print('==================================================');
print('ArangoDB initialization completed successfully');
print(`Database: ${DATABASE_NAME}`);
print(`Knowledge Graph: ${GRAPH_NAME}`);
print('Collections: users, sessions, entities, events, suggestions, relationships');
print('Indexes created for optimal query performance');
print('Schema validation enabled for data integrity');
print('==================================================');
