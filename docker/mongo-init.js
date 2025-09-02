// MongoDB initialization script for Human-AI Co-Creation Platform
// This script creates database, collections, indexes, and validation schemas
// It is idempotent and safe to run multiple times

// Switch to the application database
db = db.getSiblingDB('human_ai_co_create');

// Create application user if not exists
try {
    const appUser = 'app_user';
    const appPassword = process.env.MONGO_APP_PASSWORD || 'change_me_in_production';
    
    if (!db.getUser(appUser)) {
        db.createUser({
            user: appUser,
            pwd: appPassword,
            roles: [
                {
                    role: 'readWrite',
                    db: 'human_ai_co_create'
                }
            ]
        });
        print(`Created application user: ${appUser}`);
    } else {
        print(`Application user already exists: ${appUser}`);
    }
} catch (e) {
    print(`User creation error (may be expected): ${e.message}`);
}

// Collection definitions with JSON Schema validation
const collections = [
    {
        name: 'users',
        validator: {
            $jsonSchema: {
                bsonType: 'object',
                required: ['google_id', 'email', 'name', 'created_at'],
                properties: {
                    google_id: {
                        bsonType: 'string',
                        description: 'Google OAuth ID - required and unique'
                    },
                    email: {
                        bsonType: 'string',
                        pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$',
                        description: 'Valid email address - required and unique'
                    },
                    name: {
                        bsonType: 'string',
                        minLength: 1,
                        description: 'User name - required'
                    },
                    picture: {
                        bsonType: 'string',
                        description: 'Profile picture URL'
                    },
                    created_at: {
                        bsonType: 'date',
                        description: 'Account creation timestamp - required'
                    },
                    last_login: {
                        bsonType: 'date',
                        description: 'Last login timestamp'
                    },
                    preferences: {
                        bsonType: 'object',
                        properties: {
                            theme: { bsonType: 'string', enum: ['light', 'dark'] },
                            ai_mode: { bsonType: 'string', enum: ['balanced', 'creative', 'analytical', 'conservative'] },
                            suggestion_policy: { bsonType: 'string', enum: ['on_demand', 'idle_smart', 'proactive'] }
                        },
                        description: 'User preferences and settings'
                    }
                },
                additionalProperties: true
            }
        }
    },
    {
        name: 'sessions',
        validator: {
            $jsonSchema: {
                bsonType: 'object',
                required: ['user_id', 'topic', 'content', 'created_at'],
                properties: {
                    user_id: {
                        bsonType: 'objectId',
                        description: 'Reference to user - required'
                    },
                    title: {
                        bsonType: 'string',
                        description: 'Session title'
                    },
                    topic: {
                        bsonType: 'string',
                        enum: ['story', 'lesson_plan', 'guide', 'essay', 'other'],
                        description: 'Session topic type - required'
                    },
                    topic_descriptor: {
                        bsonType: 'object',
                        description: 'Topic-specific configuration and context'
                    },
                    content: {
                        bsonType: 'object',
                        properties: {
                            story_so_far: { bsonType: 'string' },
                            topic_content: { bsonType: 'string' },
                            events: { bsonType: 'array' },
                            characters: { bsonType: 'array' },
                            constraints: { bsonType: 'object' }
                        },
                        description: 'Session content and workspace data - required'
                    },
                    mode: {
                        bsonType: 'string',
                        enum: ['balanced', 'creative', 'analytical', 'conservative'],
                        description: 'AI assistance mode'
                    },
                    workspace: {
                        bsonType: 'object',
                        description: 'Current workspace state and metadata'
                    },
                    created_at: {
                        bsonType: 'date',
                        description: 'Session creation timestamp - required'
                    },
                    updated_at: {
                        bsonType: 'date',
                        description: 'Last update timestamp'
                    },
                    tags: {
                        bsonType: 'array',
                        items: { bsonType: 'string' },
                        description: 'Session tags for organization'
                    },
                    status: {
                        bsonType: 'string',
                        enum: ['active', 'archived', 'deleted'],
                        description: 'Session status'
                    }
                },
                additionalProperties: true
            }
        }
    },
    {
        name: 'knowledge_graph_nodes',
        validator: {
            $jsonSchema: {
                bsonType: 'object',
                required: ['session_id', 'node_type', 'name'],
                properties: {
                    session_id: {
                        bsonType: 'objectId',
                        description: 'Reference to session - required'
                    },
                    node_type: {
                        bsonType: 'string',
                        enum: ['entity', 'event'],
                        description: 'Type of knowledge graph node - required'
                    },
                    name: {
                        bsonType: 'string',
                        minLength: 1,
                        description: 'Node name or summary - required'
                    },
                    attributes: {
                        bsonType: 'object',
                        description: 'Node attributes and metadata'
                    },
                    embedding: {
                        bsonType: 'array',
                        items: { bsonType: 'double' },
                        description: 'Vector embedding for similarity search'
                    },
                    importance_score: {
                        bsonType: 'double',
                        minimum: 0,
                        maximum: 1,
                        description: 'Importance score for pruning decisions'
                    },
                    created_at: {
                        bsonType: 'date',
                        description: 'Node creation timestamp'
                    },
                    updated_at: {
                        bsonType: 'date',
                        description: 'Last update timestamp'
                    }
                },
                additionalProperties: true
            }
        }
    },
    {
        name: 'knowledge_graph_edges',
        validator: {
            $jsonSchema: {
                bsonType: 'object',
                required: ['session_id', 'from_node_id', 'to_node_id', 'relationship_type'],
                properties: {
                    session_id: {
                        bsonType: 'objectId',
                        description: 'Reference to session - required'
                    },
                    from_node_id: {
                        bsonType: 'objectId',
                        description: 'Source node reference - required'
                    },
                    to_node_id: {
                        bsonType: 'objectId',
                        description: 'Target node reference - required'
                    },
                    relationship_type: {
                        bsonType: 'string',
                        enum: ['causal', 'temporal', 'co_ref', 'attribute', 'involves', 'located_in', 'part_of'],
                        description: 'Type of relationship - required'
                    },
                    strength: {
                        bsonType: 'double',
                        minimum: 0,
                        maximum: 1,
                        description: 'Relationship strength score'
                    },
                    metadata: {
                        bsonType: 'object',
                        description: 'Additional relationship metadata'
                    },
                    created_at: {
                        bsonType: 'date',
                        description: 'Edge creation timestamp'
                    }
                },
                additionalProperties: true
            }
        }
    },
    {
        name: 'suggestions',
        validator: {
            $jsonSchema: {
                bsonType: 'object',
                required: ['session_id', 'user_id', 'branches', 'created_at'],
                properties: {
                    session_id: {
                        bsonType: 'objectId',
                        description: 'Reference to session - required'
                    },
                    user_id: {
                        bsonType: 'objectId',
                        description: 'Reference to user - required'
                    },
                    branches: {
                        bsonType: 'array',
                        maxItems: 3,
                        items: {
                            bsonType: 'object',
                            required: ['title', 'content', 'score'],
                            properties: {
                                title: { bsonType: 'string' },
                                content: { bsonType: 'string' },
                                score: { bsonType: 'double' },
                                flags: { bsonType: 'object' }
                            }
                        },
                        description: 'Generated suggestion branches (max 3) - required'
                    },
                    trigger_context: {
                        bsonType: 'object',
                        description: 'Context that triggered the suggestion'
                    },
                    acceptability_scores: {
                        bsonType: 'object',
                        description: 'Detailed scoring breakdown for each branch'
                    },
                    created_at: {
                        bsonType: 'date',
                        description: 'Suggestion creation timestamp - required'
                    },
                    accepted_branch: {
                        bsonType: 'int',
                        minimum: 0,
                        maximum: 2,
                        description: 'Index of accepted branch (0-2)'
                    },
                    feedback: {
                        bsonType: 'object',
                        description: 'User feedback on suggestions'
                    }
                },
                additionalProperties: true
            }
        }
    }
];

// Create collections with validation
collections.forEach(colDef => {
    try {
        if (!db.getCollectionNames().includes(colDef.name)) {
            db.createCollection(colDef.name, {
                validator: colDef.validator,
                validationLevel: 'moderate',
                validationAction: 'warn'
            });
            print(`Created collection with validation: ${colDef.name}`);
        } else {
            // Update validation rules for existing collections
            db.runCommand({
                collMod: colDef.name,
                validator: colDef.validator,
                validationLevel: 'moderate'
            });
            print(`Updated validation for existing collection: ${colDef.name}`);
        }
    } catch (e) {
        print(`Error with collection ${colDef.name}: ${e.message}`);
    }
});

// Create indexes for performance optimization
const indexes = [
    // Users collection indexes
    { collection: 'users', index: { 'google_id': 1 }, options: { unique: true } },
    { collection: 'users', index: { 'email': 1 }, options: { unique: true } },
    { collection: 'users', index: { 'created_at': 1 } },
    { collection: 'users', index: { 'last_login': -1 } },
    
    // Sessions collection indexes
    { collection: 'sessions', index: { 'user_id': 1 } },
    { collection: 'sessions', index: { 'topic': 1 } },
    { collection: 'sessions', index: { 'status': 1 } },
    { collection: 'sessions', index: { 'created_at': -1 } },
    { collection: 'sessions', index: { 'updated_at': -1 } },
    { collection: 'sessions', index: { 'user_id': 1, 'status': 1 } },
    { collection: 'sessions', index: { 'user_id': 1, 'updated_at': -1 } },
    { collection: 'sessions', index: { 'tags': 1 } },
    
    // Knowledge graph nodes indexes
    { collection: 'knowledge_graph_nodes', index: { 'session_id': 1 } },
    { collection: 'knowledge_graph_nodes', index: { 'node_type': 1 } },
    { collection: 'knowledge_graph_nodes', index: { 'importance_score': -1 } },
    { collection: 'knowledge_graph_nodes', index: { 'session_id': 1, 'node_type': 1 } },
    { collection: 'knowledge_graph_nodes', index: { 'session_id': 1, 'importance_score': -1 } },
    { collection: 'knowledge_graph_nodes', index: { 'name': 'text' } },
    
    // Knowledge graph edges indexes
    { collection: 'knowledge_graph_edges', index: { 'session_id': 1 } },
    { collection: 'knowledge_graph_edges', index: { 'from_node_id': 1 } },
    { collection: 'knowledge_graph_edges', index: { 'to_node_id': 1 } },
    { collection: 'knowledge_graph_edges', index: { 'relationship_type': 1 } },
    { collection: 'knowledge_graph_edges', index: { 'session_id': 1, 'relationship_type': 1 } },
    { collection: 'knowledge_graph_edges', index: { 'strength': -1 } },
    
    // Suggestions collection indexes
    { collection: 'suggestions', index: { 'session_id': 1 } },
    { collection: 'suggestions', index: { 'user_id': 1 } },
    { collection: 'suggestions', index: { 'created_at': -1 } },
    { collection: 'suggestions', index: { 'session_id': 1, 'created_at': -1 } },
    { collection: 'suggestions', index: { 'user_id': 1, 'created_at': -1 } },
    { collection: 'suggestions', index: { 'accepted_branch': 1 } }
];

indexes.forEach(indexDef => {
    try {
        const collection = db.getCollection(indexDef.collection);
        if (collection) {
            collection.createIndex(indexDef.index, indexDef.options || {});
            const indexName = Object.keys(indexDef.index).join('_');
            const uniqueStr = indexDef.options && indexDef.options.unique ? ' (unique)' : '';
            print(`Created index on ${indexDef.collection}: ${indexName}${uniqueStr}`);
        }
    } catch (e) {
        if (!e.message.includes('already exists')) {
            print(`Error creating index on ${indexDef.collection}: ${e.message}`);
        }
    }
});

// Insert sample data for development (only if in development mode)
if (typeof process !== 'undefined' && (process.env.NODE_ENV === 'development' || process.env.MONGO_ENV === 'development')) {
    try {
        const usersCollection = db.getCollection('users');
        const existingDevUser = usersCollection.findOne({ google_id: 'dev_user_123' });
        
        if (!existingDevUser) {
            const devUser = {
                google_id: 'dev_user_123',
                email: 'dev@example.com',
                name: 'Development User',
                picture: 'https://via.placeholder.com/100',
                created_at: new Date(),
                last_login: new Date(),
                preferences: {
                    theme: 'dark',
                    ai_mode: 'balanced',
                    suggestion_policy: 'on_demand'
                }
            };
            
            const insertResult = usersCollection.insertOne(devUser);
            print(`Created development user with ID: ${insertResult.insertedId}`);
            
            // Create a sample session for the development user
            const sessionsCollection = db.getCollection('sessions');
            const devSession = {
                user_id: insertResult.insertedId,
                title: 'Development Story Session',
                topic: 'story',
                topic_descriptor: {
                    genre: 'mystery',
                    pov: 'first',
                    protagonist: 'Detective Sarah'
                },
                content: {
                    story_so_far: 'Detective Sarah walked into the dimly lit apartment, her hand instinctively moving to her holster.',
                    events: [],
                    characters: [
                        { name: 'Detective Sarah', traits: ['observant', 'cautious', 'experienced'] }
                    ],
                    constraints: { preserve_pov: true, max_events: 4 }
                },
                mode: 'balanced',
                workspace: {},
                created_at: new Date(),
                updated_at: new Date(),
                tags: ['mystery', 'development'],
                status: 'active'
            };
            
            const sessionResult = sessionsCollection.insertOne(devSession);
            print(`Created development session with ID: ${sessionResult.insertedId}`);
        } else {
            print('Development user already exists');
        }
    } catch (e) {
        print(`Error creating development data: ${e.message}`);
    }
}

print('==================================================');
print('MongoDB initialization completed successfully');
print('Database: human_ai_co_create');
print('Collections: users, sessions, knowledge_graph_nodes, knowledge_graph_edges, suggestions');
print('JSON Schema validation enabled for data integrity');
print('Indexes created for optimal query performance');
print('==================================================');
