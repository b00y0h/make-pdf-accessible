#!/usr/bin/env python3
"""
Simple seed script for PDF Accessibility Service local development.
Creates sample documents and jobs directly in MongoDB.
"""

import json
import random
import uuid
from datetime import datetime, timedelta

import boto3
import pymongo


def main():
    """Main seeding function."""
    print("🚀 Simple Seed Script for PDF Accessibility Service")
    print("=" * 60)

    # MongoDB connection
    mongodb_uri = "mongodb://localhost:27017/pdf_accessibility?replicaSet=rs0"
    try:
        client = pymongo.MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✅ Connected to MongoDB")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False

    db = client.pdf_accessibility

    # Clear existing data
    print("🧹 Clearing existing data...")
    db.documents.delete_many({})
    db.jobs.delete_many({})
    print("✅ Existing data cleared")

    # Sample users (for reference)
    users = [
        {'sub': 'user_alice_developer', 'name': 'Alice Johnson'},
        {'sub': 'user_bob_designer', 'name': 'Bob Smith'},
        {'sub': 'user_carol_admin', 'name': 'Carol Wilson'},
        {'sub': 'user_david_client', 'name': 'David Lee'},
        {'sub': 'user_eve_tester', 'name': 'Eve Taylor'}
    ]

    # Create sample documents
    print("📄 Creating sample documents...")
    documents = []
    jobs = []

    statuses = ["pending", "processing", "completed", "failed", "validation_failed"]
    steps = ["structure", "ocr", "tagger", "validator", "exporter", "notifier"]

    for i in range(15):
        doc_id = str(uuid.uuid4())
        user = random.choice(users)
        status = random.choice(statuses)
        created_time = datetime.now() - timedelta(days=random.randint(0, 30))

        document = {
            "docId": doc_id,
            "ownerId": user['sub'],
            "status": status,
            "filename": f"sample-document-{i+1}.pdf",
            "createdAt": created_time,
            "updatedAt": created_time + timedelta(minutes=random.randint(1, 60)),
            "metadata": {
                "size": random.randint(100000, 5000000),
                "pages": random.randint(1, 50),
                "source": "seed_script"
            },
            "artifacts": {}
        }

        if status == "completed":
            document["completedAt"] = document["updatedAt"]
            document["artifacts"] = {
                "structured_pdf": f"s3://pdf-accessibility-processed/{doc_id}/structured.pdf",
                "accessibility_report": f"s3://pdf-accessibility-reports/{doc_id}/report.json"
            }

        documents.append(document)

        # Create related jobs
        for step in steps[:random.randint(1, len(steps))]:
            job_id = str(uuid.uuid4())
            job_status = "completed" if status == "completed" else random.choice(["pending", "running", "completed", "failed"])

            job = {
                "jobId": job_id,
                "docId": doc_id,
                "ownerId": user['sub'],
                "step": step,
                "status": job_status,
                "priority": random.choice([True, False]),
                "createdAt": created_time,
                "updatedAt": created_time + timedelta(minutes=random.randint(1, 30))
            }
            jobs.append(job)

    # Insert documents and jobs
    if documents:
        result = db.documents.insert_many(documents)
        print(f"✅ Created {len(result.inserted_ids)} documents")

    if jobs:
        result = db.jobs.insert_many(jobs)
        print(f"✅ Created {len(result.inserted_ids)} jobs")

    # Create sample files in LocalStack S3
    print("☁️  Creating sample files in LocalStack S3...")
    try:
        s3 = boto3.client(
            's3',
            endpoint_url='http://localhost:4566',
            aws_access_key_id='test',
            aws_secret_access_key='test',
            region_name='us-east-1'
        )

        # Upload some test files
        for i in range(3):
            s3.put_object(
                Bucket='pdf-accessibility-uploads',
                Key=f'test/sample-{i+1}.pdf',
                Body=f'Sample PDF content {i+1}'.encode()
            )

        s3.put_object(
            Bucket='pdf-accessibility-reports',
            Key='test/sample-report.json',
            Body=json.dumps({"test": "report", "issues": []}).encode()
        )

        print("✅ Sample files created in S3")

    except Exception as e:
        print(f"⚠️  S3 seeding failed: {e}")

    print("\n🎉 Database seeding completed successfully!")
    print("📊 Summary:")
    print(f"  - Documents: {db.documents.count_documents({})}")
    print(f"  - Jobs: {db.jobs.count_documents({})}")
    print(f"  - Sample users: {len(users)}")

    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
