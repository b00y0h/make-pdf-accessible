#!/usr/bin/env tsx

/**
 * Admin User Seeding Script
 * 
 * Creates or updates an admin user for the PDF Accessibility Service.
 * Reads configuration from environment variables:
 * - ADMIN_USERNAME: Username for admin login
 * - ADMIN_PASSWORD: Password for admin login (will be hashed)
 * - ADMIN_EMAIL: Email address for admin user
 */

import { PrismaClient } from '@prisma/client'
import bcrypt from 'bcryptjs'
import dotenv from 'dotenv'
import path from 'path'

// Load environment variables from dashboard/.env.local
dotenv.config({ path: path.join(process.cwd(), 'dashboard', '.env.local') })

const prisma = new PrismaClient()

interface AdminConfig {
  username: string
  password: string
  email: string
}

function getAdminConfig(): AdminConfig {
  const username = process.env.ADMIN_USERNAME
  const password = process.env.ADMIN_PASSWORD
  const email = process.env.ADMIN_EMAIL

  if (!username || !password || !email) {
    console.error('❌ Missing required environment variables:')
    if (!username) console.error('  - ADMIN_USERNAME')
    if (!password) console.error('  - ADMIN_PASSWORD')
    if (!email) console.error('  - ADMIN_EMAIL')
    console.error('\nPlease set these in dashboard/.env.local')
    process.exit(1)
  }

  return { username, password, email }
}

async function hashPassword(password: string): Promise<string> {
  const saltRounds = 12
  return await bcrypt.hash(password, saltRounds)
}

async function createOrUpdateAdminUser(config: AdminConfig) {
  console.log('🔐 Hashing admin password...')
  const hashedPassword = await hashPassword(config.password)

  console.log('👤 Creating/updating admin user...')

  const admin = await prisma.user.upsert({
    where: { email: config.email },
    update: {
      username: config.username,
      password: hashedPassword,
      role: 'admin',
      name: 'System Administrator',
      updatedAt: new Date(),
    },
    create: {
      email: config.email,
      username: config.username,
      password: hashedPassword,
      role: 'admin',
      name: 'System Administrator',
    },
  })

  return admin
}

async function createAuditLog(adminUserId: string, action: string) {
  await prisma.auditLog.create({
    data: {
      actorUserId: adminUserId,
      action,
      meta: {
        source: 'seed-admin-script',
        timestamp: new Date().toISOString(),
      },
    },
  })
}

async function main() {
  console.log('🚀 PDF Accessibility Service - Admin User Seeder')
  console.log('=' * 55)
  console.log('')

  try {
    // Check database connection
    console.log('📊 Checking database connection...')
    await prisma.$connect()
    console.log('✅ Database connected successfully')

    // Get admin configuration
    const config = getAdminConfig()
    console.log(`📧 Admin email: ${config.email}`)
    console.log(`👤 Admin username: ${config.username}`)

    // Create or update admin user
    const admin = await createOrUpdateAdminUser(config)
    
    // Create audit log entry
    await createAuditLog(admin.id, 'admin.user_seeded')

    console.log('')
    console.log('✅ Admin user created/updated successfully!')
    console.log('')
    console.log('📝 Admin User Details:')
    console.log(`   ID: ${admin.id}`)
    console.log(`   Email: ${admin.email}`)
    console.log(`   Username: ${admin.username}`)
    console.log(`   Role: ${admin.role}`)
    console.log(`   Created: ${admin.createdAt.toISOString()}`)
    console.log(`   Updated: ${admin.updatedAt.toISOString()}`)
    console.log('')
    console.log('🎯 Next Steps:')
    console.log('   1. Start the development server: pnpm run dev')
    console.log('   2. Navigate to: http://localhost:3001/login')
    console.log(`   3. Login with username: ${config.username}`)
    console.log('   4. Access admin panel: http://localhost:3001/admin')
    console.log('')

  } catch (error) {
    console.error('❌ Error seeding admin user:', error)
    
    if (error instanceof Error) {
      if (error.message.includes('connect')) {
        console.error('')
        console.error('💡 Database connection failed. Make sure:')
        console.error('   1. PostgreSQL is running on localhost:5432')
        console.error('   2. DATABASE_URL is correct in .env.local')
        console.error('   3. The database exists and is accessible')
      }
    }
    
    process.exit(1)
  } finally {
    await prisma.$disconnect()
  }
}

// Handle unhandled promise rejections
process.on('unhandledRejection', (error) => {
  console.error('❌ Unhandled promise rejection:', error)
  process.exit(1)
})

// Run the script
main()