#!/usr/bin/env node

/**
 * Basic Authentication Test
 * Tests the BetterAuth endpoints to ensure they're responding correctly
 */

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

async function testEndpoint(name, url, options = {}) {
  try {
    const response = await fetch(url, options);
    const status = response.status;
    const contentType = response.headers.get('content-type');

    console.log(`✓ ${name}: ${status} ${contentType || ''}`);

    if (contentType?.includes('application/json')) {
      const data = await response.json();
      return { status, data };
    }

    return { status };
  } catch (error) {
    console.error(`✗ ${name}: ${error.message}`);
    return { error: error.message };
  }
}

async function runTests() {
  console.log('🧪 Testing Authentication Endpoints\n');
  console.log(`Base URL: ${BASE_URL}\n`);

  // Test session endpoint
  console.log('📍 Session Management:');
  await testEndpoint(
    'GET /api/auth/get-session',
    `${BASE_URL}/api/auth/get-session`
  );

  // Test sign-in endpoint with invalid credentials
  console.log('\n📍 Sign-in Tests:');
  await testEndpoint(
    'POST /api/auth/sign-in/email (invalid)',
    `${BASE_URL}/api/auth/sign-in/email`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'test@example.com',
        password: 'wrongpassword',
      }),
    }
  );

  // Test sign-out endpoint
  console.log('\n📍 Sign-out Test:');
  await testEndpoint(
    'POST /api/auth/sign-out',
    `${BASE_URL}/api/auth/sign-out`,
    {
      method: 'POST',
    }
  );

  // Test social auth redirects (without following redirects)
  console.log('\n📍 Social Auth Endpoints:');
  const socialProviders = ['google', 'github', 'discord', 'apple', 'facebook'];

  for (const provider of socialProviders) {
    await testEndpoint(
      `GET /api/auth/${provider}`,
      `${BASE_URL}/api/auth/${provider}`,
      {
        redirect: 'manual', // Don't follow redirects
      }
    );
  }

  console.log('\n✅ Basic authentication tests complete!');
}

// Run tests
runTests().catch(console.error);
