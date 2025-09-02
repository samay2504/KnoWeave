// MongoDB initialization script for production
// This script runs when MongoDB container starts for the first time

// Switch to the application database
db = db.getSiblingDB('human_ai_co_create');

// Create application user if not exists
if (!db.getUser('app_user')) {
    db.createUser({
        user: 'app_user',
        pwd: process.env.MONGO_PASSWORD || 'change_me_in_production',
        roles: [
            {
                role: 'readWrite',
                db: 'human_ai_co_create'
            }
        ]
    });
}

// Create collections with validation
db.createCollection('users', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['google_id', 'email', 'name'],
            properties: {
                google_id: {
                    bsonType: 'string',
                    description: 'Google OAuth ID - required'
                },
                email: {
                    bsonType: 'string',
                    pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                    description: 'Valid email address - required'
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
                    description: 'Account creation timestamp'
                },
                last_login: {
                    bsonType: 'date',
                    description: 'Last login timestamp'
                },
                preferences: {
                    bsonType: 'object',
                    description: 'User preferences and settings'
                }
            }
        }
    }
});

db.createCollection('sessions', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['user_id', 'content', 'created_at'],
            properties: {
                user_id: {
                    bsonType: 'objectId',
                    description: 'Reference to user - required'
                },
                title: {
                    bsonType: 'string',
                    description: 'Session title'
                },
                content: {
                    bsonType: 'object',
                    description: 'Session content and data - required'
                },
                mode: {
                    bsonType: 'string',
                    enum: ['balanced', 'creative', 'analytical'],
                    description: 'AI assistance mode'
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
                    items: {
                        bsonType: 'string'
                    },
                    description: 'Session tags for organization'
                }
            }
        }
    }
});

db.createCollection('knowledge_graph', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['session_id', 'entities', 'relationships'],
            properties: {
                session_id: {
                    bsonType: 'objectId',
                    description: 'Reference to session - required'
                },
                entities: {
                    bsonType: 'array',
                    description: 'Graph entities - required'
                },
                relationships: {
                    bsonType: 'array',
                    description: 'Entity relationships - required'
                },
                created_at: {
                    bsonType: 'date',
                    description: 'Graph creation timestamp'
                },
                updated_at: {
                    bsonType: 'date',
                    description: 'Last update timestamp'
                }
            }
        }
    }
});

// Create indexes for performance
db.users.createIndex({ 'google_id': 1 }, { unique: true });
db.users.createIndex({ 'email': 1 }, { unique: true });
db.users.createIndex({ 'created_at': 1 });

db.sessions.createIndex({ 'user_id': 1 });
db.sessions.createIndex({ 'created_at': -1 });
db.sessions.createIndex({ 'updated_at': -1 });
db.sessions.createIndex({ 'tags': 1 });

db.knowledge_graph.createIndex({ 'session_id': 1 }, { unique: true });
db.knowledge_graph.createIndex({ 'updated_at': -1 });

// Insert sample data for development (only if in development mode)
if (process.env.NODE_ENV === 'development') {
    print('Inserting development sample data...');
    
    // Sample user (will only insert if doesn't exist)
    db.users.updateOne(
        { google_id: 'dev_user_123' },
        {
            $setOnInsert: {
                google_id: 'dev_user_123',
                email: 'dev@example.com',
                name: 'Development User',
                picture: 'https://via.placeholder.com/100',
                created_at: new Date(),
                last_login: new Date(),
                preferences: {
                    theme: 'dark',
                    ai_mode: 'balanced'
                }
            }
        },
        { upsert: true }
    );
}

print('MongoDB initialization completed successfully');
print('Collections created: users, sessions, knowledge_graph');
print('Indexes created for optimal performance');
print('Database ready for Human-AI Co-Creation Platform');
