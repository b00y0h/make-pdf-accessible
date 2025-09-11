import { test as setup, expect } from '@playwright/test';

/**
 * Global setup for Playwright tests.
 * Runs once before all test suites to prepare the test environment.
 */
setup('global setup', async ({ request }) => {
  console.log('🚀 Starting global test setup...');

  // Wait for services to be ready
  await waitForServices(request);

  // Setup test data
  await setupTestData(request);

  console.log('✅ Global test setup completed');
});

async function waitForServices(request: any) {
  console.log('⏳ Waiting for services to be ready...');

  const services = [
    { name: 'Web App', url: 'http://localhost:3000' },
    { name: 'Dashboard', url: 'http://localhost:3001' },
    { name: 'API', url: 'http://localhost:8000/health' },
  ];

  for (const service of services) {
    let retries = 30;
    let ready = false;

    while (retries > 0 && !ready) {
      try {
        const response = await request.get(service.url);
        if (response.ok()) {
          console.log(`✅ ${service.name} is ready`);
          ready = true;
        } else {
          throw new Error(`Status: ${response.status()}`);
        }
      } catch (error) {
        console.log(
          `⏳ Waiting for ${service.name}... (${retries} retries left)`
        );
        await new Promise((resolve) => setTimeout(resolve, 2000));
        retries--;
      }
    }

    if (!ready) {
      throw new Error(`❌ ${service.name} failed to start after 60 seconds`);
    }
  }
}

async function setupTestData(request: any) {
  console.log('📝 Setting up test data...');

  try {
    // Create test users for authentication tests
    const testUsers = [
      {
        email: 'e2e.user@example.com',
        password: 'E2ETestPass123!',
        name: 'E2E Test User',
        role: 'user',
      },
      {
        email: 'e2e.admin@example.com',
        password: 'E2EAdminPass123!',
        name: 'E2E Admin User',
        role: 'admin',
      },
    ];

    for (const user of testUsers) {
      try {
        const response = await request.post(
          'http://localhost:8000/auth/register',
          {
            data: user,
          }
        );

        if (response.ok()) {
          console.log(`✅ Created test user: ${user.email}`);
        } else {
          // User might already exist, which is fine
          console.log(`ℹ️  Test user ${user.email} might already exist`);
        }
      } catch (error) {
        console.log(`⚠️  Could not create user ${user.email}:`, error);
      }
    }

    // Setup test API keys
    await setupTestAPIKeys(request);
  } catch (error) {
    console.warn('⚠️  Warning: Test data setup encountered issues:', error);
    // Don't fail the entire setup if test data creation fails
  }
}

async function setupTestAPIKeys(request: any) {
  try {
    // First authenticate as admin
    const authResponse = await request.post(
      'http://localhost:3001/api/auth/sign-in/email',
      {
        data: {
          email: 'e2e.admin@example.com',
          password: 'E2EAdminPass123!',
        },
      }
    );

    if (authResponse.ok()) {
      const authData = await authResponse.json();
      const adminToken = authData.token;

      // Create test API key
      const apiKeyResponse = await request.post(
        'http://localhost:8000/api-keys',
        {
          headers: {
            Authorization: `Bearer ${adminToken}`,
          },
          data: {
            name: 'E2E Test API Key',
            scopes: ['documents:read', 'documents:write'],
          },
        }
      );

      if (apiKeyResponse.ok()) {
        const apiKeyData = await apiKeyResponse.json();
        console.log('✅ Created test API key');

        // Store API key for tests
        process.env.E2E_TEST_API_KEY = apiKeyData.key;
      }
    }
  } catch (error) {
    console.log('⚠️  Could not setup API keys:', error);
  }
}
