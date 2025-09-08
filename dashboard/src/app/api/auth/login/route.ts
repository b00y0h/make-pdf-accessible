import { NextRequest, NextResponse } from 'next/server'
import bcrypt from 'bcryptjs'
import { connectToDatabase } from '@/lib/mongodb'
import { User } from '@/types/admin'

interface LoginRequest {
  username: string
  password: string
}

export async function POST(request: NextRequest) {
  try {
    const { username, password }: LoginRequest = await request.json()

    if (!username || !password) {
      return NextResponse.json(
        { error: 'Username and password are required' },
        { status: 400 }
      )
    }

    // Connect to database
    const { db } = await connectToDatabase()
    const usersCollection = db.collection<User>('users')

    // Find user by username or email
    const user = await usersCollection.findOne({
      $or: [
        { username: username },
        { email: username }
      ]
    })

    if (!user) {
      return NextResponse.json(
        { error: 'Invalid credentials' },
        { status: 401 }
      )
    }

    // Verify password
    if (!user.password) {
      return NextResponse.json(
        { error: 'Invalid credentials' },
        { status: 401 }
      )
    }

    const passwordValid = await bcrypt.compare(password, user.password)
    if (!passwordValid) {
      return NextResponse.json(
        { error: 'Invalid credentials' },
        { status: 401 }
      )
    }

    // Create session (in production, you'd use proper JWT or session management)
    const sessionId = `session_${user._id}_${Date.now()}`
    
    // Remove password from response
    const { password: _, ...userWithoutPassword } = user

    return NextResponse.json({
      success: true,
      user: {
        ...userWithoutPassword,
        sub: user._id?.toString() || user.sub,
        id: user._id?.toString(),
      },
      sessionId,
    })

  } catch (error) {
    console.error('Login error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}