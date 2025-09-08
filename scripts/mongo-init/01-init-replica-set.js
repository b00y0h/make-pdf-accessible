// MongoDB initialization script for replica set and indexes
// This script runs when MongoDB container starts for the first time

print("🚀 Initializing MongoDB for PDF Accessibility Service...");

// Initialize replica set
try {
    var status = rs.status();
    print("Replica set already initialized");
} catch (e) {
    print("Initializing replica set...");
    rs.initiate({
        _id: "rs0",
        members: [
            { _id: 0, host: "localhost:27017" }
        ]
    });
    
    // Wait for replica set to be ready
    while (!rs.isMaster().ismaster) {
        sleep(1000);
    }
    print("✅ Replica set initialized successfully");
}

// Switch to pdf_accessibility database
db = db.getSiblingDB('pdf_accessibility');

print("📊 Creating collections and indexes...");

// Create documents collection with schema validation
db.createCollection("documents", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["docId", "ownerId", "status", "createdAt", "updatedAt"],
            properties: {
                docId: {
                    bsonType: "string",
                    pattern: "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
                    description: "UUID v4 document identifier"
                },
                ownerId: {
                    bsonType: "string",
                    description: "User ID who owns the document"
                },
                status: {
                    enum: ["pending", "processing", "completed", "failed", "validation_failed", "notification_failed"],
                    description: "Current document processing status"
                },
                createdAt: {
                    bsonType: "date",
                    description: "Document creation timestamp"
                },
                updatedAt: {
                    bsonType: "date", 
                    description: "Last update timestamp"
                },
                completedAt: {
                    bsonType: ["date", "null"],
                    description: "Processing completion timestamp"
                },
                filename: {
                    bsonType: ["string", "null"],
                    description: "Original filename"
                },
                sourceUrl: {
                    bsonType: ["string", "null"],
                    description: "Source URL if document was fetched"
                },
                metadata: {
                    bsonType: "object",
                    description: "Additional metadata"
                },
                artifacts: {
                    bsonType: "object",
                    description: "Generated artifacts and file locations"
                }
            }
        }
    },
    validationLevel: "moderate"
});

// Create jobs collection with schema validation  
db.createCollection("jobs", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["jobId", "docId", "ownerId", "step", "status", "createdAt", "updatedAt"],
            properties: {
                jobId: {
                    bsonType: "string",
                    pattern: "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
                    description: "UUID v4 job identifier"
                },
                docId: {
                    bsonType: "string",
                    pattern: "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
                    description: "Associated document ID"
                },
                ownerId: {
                    bsonType: "string",
                    description: "User ID who owns the document"
                },
                step: {
                    enum: ["structure", "ocr", "tagger", "validator", "exporter", "notifier"],
                    description: "Processing step name"
                },
                status: {
                    enum: ["pending", "running", "completed", "failed", "retry", "timeout"],
                    description: "Current job status"
                },
                priority: {
                    bsonType: ["bool", "number"],
                    description: "Job priority"
                },
                createdAt: {
                    bsonType: "date",
                    description: "Job creation timestamp"
                },
                updatedAt: {
                    bsonType: "date",
                    description: "Last update timestamp"
                }
            }
        }
    },
    validationLevel: "moderate"
});

print("📋 Creating indexes for optimal query performance...");

// Documents collection indexes
db.documents.createIndex(
    { "docId": 1 }, 
    { name: "idx_documents_docId", unique: true, background: true }
);

db.documents.createIndex(
    { "ownerId": 1, "createdAt": -1 }, 
    { name: "idx_documents_owner_created", background: true }
);

db.documents.createIndex(
    { "status": 1, "updatedAt": -1 }, 
    { name: "idx_documents_status_updated", background: true }
);

db.documents.createIndex(
    { "status": 1, "ownerId": 1 }, 
    { name: "idx_documents_status_owner", background: true }
);

db.documents.createIndex(
    { "createdAt": -1 }, 
    { name: "idx_documents_created_desc", background: true }
);

// Jobs collection indexes  
db.jobs.createIndex(
    { "jobId": 1 }, 
    { name: "idx_jobs_jobId", unique: true, background: true }
);

db.jobs.createIndex(
    { "docId": 1, "updatedAt": -1 }, 
    { name: "idx_jobs_doc_updated", background: true }
);

db.jobs.createIndex(
    { "status": 1, "priority": -1, "createdAt": 1 }, 
    { name: "idx_jobs_status_priority_created", background: true }
);

db.jobs.createIndex(
    { "ownerId": 1, "step": 1, "status": 1 }, 
    { name: "idx_jobs_owner_step_status", background: true }
);

db.jobs.createIndex(
    { "step": 1, "status": 1 }, 
    { name: "idx_jobs_step_status", background: true }
);

// Compound index for processing queue queries
db.jobs.createIndex(
    { "status": 1, "step": 1, "priority": -1, "createdAt": 1 }, 
    { name: "idx_jobs_processing_queue", background: true }
);

print("✅ Collections and indexes created successfully");

// Create a test document and job to verify everything works
print("🧪 Creating test data...");

var testDocId = "test-" + new Date().getTime();
var testJobId = "job-" + new Date().getTime();

// Insert test document
db.documents.insertOne({
    docId: testDocId,
    ownerId: "system-test",
    status: "pending",
    filename: "test-document.pdf",
    createdAt: new Date(),
    updatedAt: new Date(),
    metadata: {
        source: "initialization",
        test: true
    },
    artifacts: {}
});

// Insert test job
db.jobs.insertOne({
    jobId: testJobId,
    docId: testDocId,
    ownerId: "system-test", 
    step: "structure",
    status: "pending",
    priority: false,
    createdAt: new Date(),
    updatedAt: new Date()
});

print("✅ Test data created successfully");

// Display database stats
print("📊 Database initialization complete:");
print("  - Documents collection: " + db.documents.countDocuments() + " documents");
print("  - Jobs collection: " + db.jobs.countDocuments() + " jobs");
print("  - Documents indexes: " + db.documents.getIndexes().length);
print("  - Jobs indexes: " + db.jobs.getIndexes().length);

print("🎉 MongoDB initialization completed successfully!");