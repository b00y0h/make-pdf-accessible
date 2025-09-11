import { NextRequest, NextResponse } from 'next/server';
import jwt from 'jsonwebtoken';
import { auth } from '@/lib/auth-server';

const API_JWT_SECRET =
  process.env.API_JWT_SECRET || 'your-api-jwt-secret-change-in-production';

export async function POST(request: NextRequest) {
  try {
    // Get session from the request
    const session = await auth.api.getSession({
      headers: request.headers,
    });

    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Create API JWT with short expiration
    const apiToken = jwt.sign(
      {
        sub: session.user.id,
        email: session.user.email,
        name: session.user.name,
        role: session.user.role || 'user',
        orgId: session.user.orgId,
        aud: 'accesspdf-api',
        iss: 'accesspdf-dashboard',
      },
      API_JWT_SECRET,
      {
        expiresIn: '10m', // 10 minutes - short-lived for security
      }
    );

    return NextResponse.json({
      token: apiToken,
      expiresIn: 600, // 10 minutes in seconds
    });
  } catch (error) {
    console.error('API token generation error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// GET endpoint to check token validity
export async function GET(request: NextRequest) {
  try {
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    const token = authHeader.substring(7);

    try {
      const decoded = jwt.verify(token, API_JWT_SECRET) as any;

      return NextResponse.json({
        valid: true,
        user: {
          id: decoded.sub,
          email: decoded.email,
          name: decoded.name,
          role: decoded.role,
          orgId: decoded.orgId,
        },
        expiresAt: decoded.exp,
      });
    } catch (jwtError) {
      return NextResponse.json(
        { error: 'Invalid or expired token', valid: false },
        { status: 401 }
      );
    }
  } catch (error) {
    console.error('API token validation error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
