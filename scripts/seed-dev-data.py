#!/usr/bin/env python3
"""
Development seed script for PDF Accessibility Service.
Creates sample users, documents, and jobs with realistic data.
"""

import os
import sys
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

# Add services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'api'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'shared'))

def setup_environment():
    """Setup environment variables for local development."""
    os.environ.update({
        'PERSISTENCE_PROVIDER': 'mongo',
        'MONGODB_URI': 'mongodb://localhost:27017/pdf_accessibility?replicaSet=rs0',
        'MONGODB_DATABASE': 'pdf_accessibility',
        'ENABLE_QUERY_LOGGING': 'true',
        'DEBUG_MODE': 'true',
        'AWS_ENDPOINT_URL': 'http://localhost:4566',
        'AWS_DEFAULT_REGION': 'us-east-1',
        'AWS_ACCESS_KEY_ID': 'test',
        'AWS_SECRET_ACCESS_KEY': 'test',
    })

def generate_sample_users() -> List[Dict[str, Any]]:
    """Generate sample users (BetterAuth format - sub only)."""
    users = [
        {
            'sub': 'user_alice_developer',
            'email': 'alice@example.com',
            'name': 'Alice Johnson',
            'role': 'developer'
        },
        {
            'sub': 'user_bob_designer',
            'email': 'bob@example.com', 
            'name': 'Bob Smith',
            'role': 'designer'
        },
        {
            'sub': 'user_carol_admin',
            'email': 'carol@example.com',
            'name': 'Carol Wilson',
            'role': 'admin'
        },
        {
            'sub': 'user_david_client',
            'email': 'david@client.com',
            'name': 'David Brown',
            'role': 'client'
        },
        {
            'sub': 'user_eve_tester',
            'email': 'eve@example.com',
            'name': 'Eve Davis',
            'role': 'tester'
        }
    ]
    return users

def generate_document_data(users: List[Dict]) -> List[Dict[str, Any]]:
    """Generate sample documents with realistic data."""
    
    sample_filenames = [
        "annual-report-2023.pdf",
        "employee-handbook.pdf", 
        "product-brochure.pdf",
        "legal-contract.pdf",
        "technical-documentation.pdf",
        "marketing-presentation.pdf",
        "user-manual.pdf",
        "financial-statements.pdf",
        "research-paper.pdf",
        "company-policy.pdf",
        "training-materials.pdf",
        "project-proposal.pdf"
    ]
    
    statuses = [
        ("pending", 0.1),
        ("processing", 0.2), 
        ("completed", 0.6),
        ("failed", 0.05),
        ("validation_failed", 0.03),
        ("notification_failed", 0.02)
    ]
    
    documents = []
    
    for i in range(25):  # Generate 25 sample documents
        doc_id = str(uuid.uuid4())
        owner = random.choice(users)
        filename = random.choice(sample_filenames)
        
        # Weighted random status selection
        status_choices = [status for status, _ in statuses]
        status_weights = [weight for _, weight in statuses]
        status = random.choices(status_choices, weights=status_weights)[0]
        
        # Generate realistic timestamps
        created_at = datetime.utcnow() - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        updated_at = created_at + timedelta(
            hours=random.randint(1, 48),
            minutes=random.randint(0, 59)
        )
        
        completed_at = None
        if status == "completed":
            completed_at = updated_at + timedelta(
                minutes=random.randint(5, 120)
            )
        
        # Generate artifacts for completed documents
        artifacts = {}
        if status == "completed":
            artifacts = {
                "processed_pdf": f"processed/{doc_id}/{doc_id}.pdf",
                "html_version": f"processed/{doc_id}/{doc_id}.html", 
                "accessibility_report": f"reports/{doc_id}/accessibility_report.json",
                "structured_data": f"processed/{doc_id}/structure.json",
                "ocr_data": f"processed/{doc_id}/ocr.json"
            }
        
        # Generate metadata
        metadata = {
            "original_size": random.randint(50000, 5000000),  # 50KB to 5MB
            "pages": random.randint(1, 50),
            "language": random.choice(["en", "es", "fr", "de"]),
            "source": random.choice(["upload", "url", "email"]),
            "priority": random.choice([True, False])
        }
        
        # Add webhook URL occasionally
        webhook_url = None
        if random.random() < 0.3:  # 30% chance
            webhook_url = f"https://api.example.com/webhooks/{owner['sub']}"
        
        document = {
            "docId": doc_id,
            "ownerId": owner['sub'],
            "status": status,
            "filename": filename,
            "createdAt": created_at,
            "updatedAt": updated_at,
            "completedAt": completed_at,
            "metadata": metadata,
            "artifacts": artifacts
        }
        
        if webhook_url:
            document["webhookUrl"] = webhook_url
            
        # Add error message for failed documents
        if "failed" in status:
            error_messages = [
                "PDF parsing failed: Corrupted file structure",
                "OCR processing timeout after 5 minutes", 
                "Invalid PDF format: Cannot extract text",
                "Network error: Unable to download from source URL",
                "Validation failed: Document contains no readable text"
            ]
            document["errorMessage"] = random.choice(error_messages)
        
        documents.append(document)
    
    return documents

def generate_job_data(documents: List[Dict]) -> List[Dict[str, Any]]:
    """Generate jobs for the documents."""
    
    steps = ["structure", "ocr", "tagger", "validator", "exporter", "notifier"]
    job_statuses = [
        ("pending", 0.1),
        ("running", 0.1), 
        ("completed", 0.7),
        ("failed", 0.05),
        ("retry", 0.03),
        ("timeout", 0.02)
    ]
    
    jobs = []
    
    for document in documents:
        doc_status = document["status"]
        doc_id = document["docId"]
        owner_id = document["ownerId"]
        
        # Determine how many jobs to create based on document status
        if doc_status == "pending":
            # Only initial job
            job_count = 1
        elif doc_status == "processing": 
            # Partially completed jobs
            job_count = random.randint(1, 4)
        elif doc_status == "completed":
            # All jobs completed
            job_count = len(steps)
        else:
            # Failed somewhere in the pipeline
            job_count = random.randint(1, len(steps))
        
        for i in range(job_count):
            job_id = str(uuid.uuid4())
            step = steps[i]
            
            # Determine job status
            if doc_status == "completed" and i < job_count:
                job_status = "completed"
            elif doc_status == "processing" and i == job_count - 1:
                job_status = "running"
            elif doc_status == "failed" and i == job_count - 1:
                job_status = "failed"
            else:
                status_choices = [status for status, _ in job_statuses]
                status_weights = [weight for _, weight in job_statuses]
                job_status = random.choices(status_choices, weights=status_weights)[0]
            
            # Generate timestamps relative to document
            created_at = document["createdAt"] + timedelta(minutes=i * 5)
            updated_at = created_at + timedelta(
                minutes=random.randint(1, 30)
            )
            
            started_at = None
            completed_at = None
            
            if job_status in ["running", "completed", "failed"]:
                started_at = created_at + timedelta(minutes=random.randint(1, 5))
                
            if job_status in ["completed", "failed"]:
                completed_at = started_at + timedelta(
                    minutes=random.randint(2, 20)
                )
                updated_at = completed_at
            
            # Generate job details
            job = {
                "jobId": job_id,
                "docId": doc_id,
                "ownerId": owner_id,
                "step": step,
                "status": job_status,
                "priority": document["metadata"].get("priority", False),
                "createdAt": created_at,
                "updatedAt": updated_at,
                "attempts": 1 if job_status != "retry" else random.randint(2, 4),
                "worker": {
                    "id": f"worker-{random.randint(1, 5)}",
                    "version": "1.0.0"
                }
            }
            
            if started_at:
                job["startedAt"] = started_at
            if completed_at:
                job["completedAt"] = completed_at
            
            # Add error details for failed jobs
            if job_status == "failed":
                error_messages = {
                    "structure": "Failed to parse PDF structure",
                    "ocr": "OCR processing failed: Low quality image", 
                    "tagger": "Tagging failed: Unsupported document format",
                    "validator": "Validation failed: Accessibility issues found",
                    "exporter": "Export failed: Insufficient disk space",
                    "notifier": "Notification failed: Invalid webhook URL"
                }
                job["error"] = error_messages.get(step, "Unknown error occurred")
            
            # Add processing logs
            if job_status in ["completed", "failed"]:
                job["logs"] = [
                    {"timestamp": created_at.isoformat(), "level": "INFO", "message": f"Starting {step} processing"},
                    {"timestamp": (started_at or created_at).isoformat(), "level": "INFO", "message": f"{step} worker assigned"},
                    {"timestamp": updated_at.isoformat(), "level": "INFO" if job_status == "completed" else "ERROR", "message": f"{step} processing {'completed' if job_status == 'completed' else 'failed'}"}
                ]
            
            jobs.append(job)
    
    return jobs

async def seed_database():
    """Seed the database with sample data."""
    
    print("🌱 Starting database seeding...")
    
    try:
        from services.shared.persistence import get_persistence_manager
        
        pm = get_persistence_manager()
        
        print("✅ Connected to database")
        
        # Generate sample data
        print("📊 Generating sample data...")
        users = generate_sample_users()
        documents = generate_document_data(users)
        jobs = generate_job_data(documents)
        
        print(f"Generated {len(users)} users, {len(documents)} documents, {len(jobs)} jobs")
        
        # Clear existing data (be careful in production!)
        print("🧹 Clearing existing data...")
        try:
            # This would clear collections - implement based on your repository
            print("⚠️  Data clearing not implemented - appending to existing data")
        except Exception as e:
            print(f"Warning: Could not clear existing data: {e}")
        
        # Insert documents
        print("📄 Inserting documents...")
        for i, doc in enumerate(documents):
            try:
                result = pm.create_document(doc)
                if (i + 1) % 5 == 0:
                    print(f"  Inserted {i + 1}/{len(documents)} documents")
            except Exception as e:
                print(f"❌ Failed to insert document {doc['docId']}: {e}")
        
        # Insert jobs  
        print("⚙️  Inserting jobs...")
        for i, job in enumerate(jobs):
            try:
                result = pm.create_job(job)
                if (i + 1) % 10 == 0:
                    print(f"  Inserted {i + 1}/{len(jobs)} jobs")
            except Exception as e:
                print(f"❌ Failed to insert job {job['jobId']}: {e}")
        
        # Display summary
        print("\n📊 Seeding Summary:")
        print(f"✅ Users: {len(users)} (reference only)")
        print(f"✅ Documents: {len(documents)} inserted")
        print(f"✅ Jobs: {len(jobs)} inserted")
        
        print("\n👥 Sample Users:")
        for user in users[:3]:
            print(f"  - {user['name']} ({user['sub']}) - {user['role']}")
        
        print("\n📈 Document Status Distribution:")
        status_counts = {}
        for doc in documents:
            status = doc['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in sorted(status_counts.items()):
            print(f"  - {status}: {count}")
        
        print("\n🎯 You can now:")
        print("  1. Access Mongo Express: http://localhost:8081 (admin/admin123)")
        print("  2. Access LocalStack: http://localhost:4566")
        print("  3. Start the API: make dev-api")
        print("  4. Start the dashboard: make dev-dashboard")
        
        print("\n🎉 Database seeding completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_sample_files():
    """Create sample PDF files in LocalStack S3."""
    print("📁 Creating sample files in S3...")
    
    try:
        import boto3
        from botocore.config import Config
        
        s3 = boto3.client(
            's3',
            endpoint_url='http://localhost:4566',
            aws_access_key_id='test',
            aws_secret_access_key='test',
            region_name='us-east-1',
            config=Config(signature_version='s3v4')
        )
        
        # Create sample PDF content
        sample_files = [
            {
                'key': 'uploads/annual-report-2023.pdf',
                'content': b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Sample Annual Report) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000174 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n265\n%%EOF'
            },
            {
                'key': 'uploads/employee-handbook.pdf', 
                'content': b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Employee Handbook) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000174 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n265\n%%EOF'
            }
        ]
        
        bucket = 'pdf-accessibility-uploads'
        
        for file_info in sample_files:
            try:
                s3.put_object(
                    Bucket=bucket,
                    Key=file_info['key'],
                    Body=file_info['content'],
                    ContentType='application/pdf'
                )
                print(f"  ✅ Uploaded {file_info['key']}")
            except Exception as e:
                print(f"  ❌ Failed to upload {file_info['key']}: {e}")
        
        print("✅ Sample files created in S3")
        
    except Exception as e:
        print(f"❌ Failed to create sample files: {e}")

async def main():
    """Main seeding function."""
    print("🚀 PDF Accessibility Service - Development Data Seeder")
    print("=" * 60)
    
    # Setup environment
    setup_environment()
    
    # Wait for services to be ready
    print("⏳ Checking if services are ready...")
    
    import time
    import pymongo
    
    # Check MongoDB
    max_retries = 30
    for i in range(max_retries):
        try:
            client = pymongo.MongoClient('mongodb://localhost:27017/?replicaSet=rs0', serverSelectionTimeoutMS=1000)
            client.admin.command('ismaster')
            client.close()
            print("✅ MongoDB is ready")
            break
        except Exception:
            if i == max_retries - 1:
                print("❌ MongoDB is not ready after 30 seconds")
                return False
            print(f"Waiting for MongoDB... ({i+1}/30)")
            time.sleep(1)
    
    # Check LocalStack
    for i in range(max_retries):
        try:
            import requests
            response = requests.get('http://localhost:4566/_localstack/health', timeout=1)
            if response.status_code == 200:
                print("✅ LocalStack is ready") 
                break
        except Exception:
            if i == max_retries - 1:
                print("❌ LocalStack is not ready after 30 seconds")
                return False
            print(f"Waiting for LocalStack... ({i+1}/30)")
            time.sleep(1)
    
    # Seed database
    success = await seed_database()
    
    if success:
        # Create sample files
        create_sample_files()
        print("\n🎉 All seeding completed successfully!")
        return True
    else:
        print("\n❌ Seeding failed")
        return False

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)