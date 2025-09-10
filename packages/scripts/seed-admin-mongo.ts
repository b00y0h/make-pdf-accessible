#!/usr/bin/env tsx

/**
 * MongoDB Admin User Seeding Script
 *
 * Creates or updates an admin user for the PDF Accessibility Service using MongoDB.
 * Reads configuration from environment variables:
 * - ADMIN_USERNAME: Username for admin login
 * - ADMIN_PASSWORD: Password for admin login (will be hashed)
 * - ADMIN_EMAIL: Email address for admin user
 */

import { MongoClient, Db } from 'mongodb';
import bcrypt from 'bcryptjs';
import dotenv from 'dotenv';
import path from 'path';

// Load environment variables from dashboard/.env.local
dotenv.config({ path: path.join(process.cwd(), 'dashboard', '.env.local') });

interface AdminConfig {
  username: string;
  password: string;
  email: string;
}

function getAdminConfig(): AdminConfig {
  const username = process.env.ADMIN_USERNAME;
  const password = process.env.ADMIN_PASSWORD;
  const email = process.env.ADMIN_EMAIL;

  if (!username || !password || !email) {
    console.error('❌ Missing required environment variables:');
    if (!username) console.error('  - ADMIN_USERNAME');
    if (!password) console.error('  - ADMIN_PASSWORD');
    if (!email) console.error('  - ADMIN_EMAIL');
    console.error('\\nPlease set these in dashboard/.env.local');
    process.exit(1);
  }

  return { username, password, email };
}

async function hashPassword(password: string): Promise<string> {
  const saltRounds = 12;
  return await bcrypt.hash(password, saltRounds);
}

async function connectToMongoDB(): Promise<{ client: MongoClient; db: Db }> {
  const uri =
    process.env.MONGODB_URI ||
    'mongodb://localhost:27017/pdf_accessibility?replicaSet=rs0';
  const dbName = process.env.MONGODB_DATABASE || 'pdf_accessibility';

  const client = new MongoClient(uri);
  await client.connect();
  const db = client.db(dbName);

  return { client, db };
}

async function createOrUpdateAdminUser(db: Db, config: AdminConfig) {
  console.log('🔐 Hashing admin password...');
  const hashedPassword = await hashPassword(config.password);

  console.log('👤 Creating/updating admin user...');

  const now = new Date();
  const usersCollection = db.collection('users');

  // Check if user already exists
  const existingUser = await usersCollection.findOne({ email: config.email });

  let admin;
  if (existingUser) {
    // Update existing user
    admin = await usersCollection.findOneAndUpdate(
      { email: config.email },
      {
        $set: {
          username: config.username,
          password: hashedPassword,
          role: 'admin',
          name: 'System Administrator',
          updatedAt: now,
        },
      },
      { returnDocument: 'after' }
    );
    admin = admin.value;
  } else {
    // Create new user
    const newUser = {
      email: config.email,
      username: config.username,
      password: hashedPassword,
      role: 'admin',
      name: 'System Administrator',
      createdAt: now,
      updatedAt: now,
    };

    const result = await usersCollection.insertOne(newUser);
    admin = { ...newUser, _id: result.insertedId };
  }

  return admin;
}

async function createAuditLog(db: Db, adminUserId: string, action: string) {
  const auditLogsCollection = db.collection('auditLogs');

  await auditLogsCollection.insertOne({
    actorUserId: adminUserId,
    action,
    meta: {
      source: 'seed-admin-script',
      timestamp: new Date().toISOString(),
    },
    createdAt: new Date(),
  });
}

async function main() {
  console.log('🚀 PDF Accessibility Service - MongoDB Admin User Seeder');
  console.log('=' * 60);
  console.log('');

  try {
    // Check MongoDB connection
    console.log('📊 Connecting to MongoDB...');
    const { client, db } = await connectToMongoDB();
    console.log('✅ MongoDB connected successfully');

    // Get admin configuration
    const config = getAdminConfig();
    console.log(`📧 Admin email: ${config.email}`);
    console.log(`👤 Admin username: ${config.username}`);

    // Create or update admin user
    const admin = await createOrUpdateAdminUser(db, config);

    // Create audit log entry
    await createAuditLog(db, admin._id.toString(), 'admin.user_seeded');

    console.log('');
    console.log('✅ Admin user created/updated successfully!');
    console.log('');
    console.log('📝 Admin User Details:');
    console.log(`   ID: ${admin._id}`);
    console.log(`   Email: ${admin.email}`);
    console.log(`   Username: ${admin.username}`);
    console.log(`   Role: ${admin.role}`);
    console.log(`   Created: ${admin.createdAt.toISOString()}`);
    console.log(`   Updated: ${admin.updatedAt.toISOString()}`);
    console.log('');
    console.log('🎯 Next Steps:');
    console.log('   1. Start the development server: pnpm run dev');
    console.log('   2. Navigate to: http://localhost:3001/sign-in');
    console.log(`   3. Login with username: ${config.username}`);
    console.log('   4. Access admin panel: http://localhost:3001/admin');
    console.log('');

    await client.close();
  } catch (error) {
    console.error('❌ Error seeding admin user:', error);

    if (error instanceof Error) {
      if (error.message.includes('connect')) {
        console.error('');
        console.error('💡 MongoDB connection failed. Make sure:');
        console.error('   1. MongoDB is running: make up');
        console.error('   2. Replica set is initialized: make seed');
        console.error('   3. Connection string is correct in .env.local');
      }
    }

    process.exit(1);
  }
}

// Handle unhandled promise rejections
process.on('unhandledRejection', (error) => {
  console.error('❌ Unhandled promise rejection:', error);
  process.exit(1);
});

// Run the script
main();
