import { test as teardown } from '@playwright/test';

/**
 * Global teardown for Playwright tests.
 * Runs once after all test suites to clean up the test environment.
 */
teardown('global teardown', async ({ request }) => {
  console.log('🧹 Starting global test teardown...');

  // Clean up test data
  await cleanupTestData(request);

  console.log('✅ Global test teardown completed');
});

async function cleanupTestData(request: any) {
  console.log('🗑️  Cleaning up test data...');

  try {
    // Clean up test users
    const testUserEmails = ['e2e.user@example.com', 'e2e.admin@example.com'];

    for (const email of testUserEmails) {
      try {
        // First get admin token
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

          // Find user by email
          const usersResponse = await request.get(
            'http://localhost:8000/admin/users',
            {
              headers: {
                Authorization: `Bearer ${adminToken}`,
              },
              params: {
                email: email,
              },
            }
          );

          if (usersResponse.ok()) {
            const usersData = await usersResponse.json();

            if (usersData.users && usersData.users.length > 0) {
              const userId = usersData.users[0].id;

              // Delete user
              const deleteResponse = await request.delete(
                `http://localhost:8000/admin/users/${userId}`,
                {
                  headers: {
                    Authorization: `Bearer ${adminToken}`,
                  },
                }
              );

              if (deleteResponse.ok()) {
                console.log(`✅ Cleaned up test user: ${email}`);
              }
            }
          }
        }
      } catch (error) {
        console.log(`⚠️  Could not cleanup user ${email}:`, error);
      }
    }

    // Clean up test API keys
    await cleanupTestAPIKeys(request);

    // Clean up uploaded test files
    await cleanupTestFiles(request);
  } catch (error) {
    console.warn('⚠️  Warning: Test data cleanup encountered issues:', error);
  }
}

async function cleanupTestAPIKeys(request: any) {
  try {
    // Get admin token
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

      // Get all API keys
      const apiKeysResponse = await request.get(
        'http://localhost:8000/api-keys',
        {
          headers: {
            Authorization: `Bearer ${adminToken}`,
          },
        }
      );

      if (apiKeysResponse.ok()) {
        const apiKeysData = await apiKeysResponse.json();

        // Delete test API keys
        for (const apiKey of apiKeysData.keys || []) {
          if (apiKey.name.includes('E2E Test')) {
            const deleteResponse = await request.delete(
              `http://localhost:8000/api-keys/${apiKey.id}`,
              {
                headers: {
                  Authorization: `Bearer ${adminToken}`,
                },
              }
            );

            if (deleteResponse.ok()) {
              console.log(`✅ Cleaned up API key: ${apiKey.name}`);
            }
          }
        }
      }
    }
  } catch (error) {
    console.log('⚠️  Could not cleanup API keys:', error);
  }
}

async function cleanupTestFiles(request: any) {
  try {
    // Get admin token
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

      // Get all documents
      const documentsResponse = await request.get(
        'http://localhost:8000/documents',
        {
          headers: {
            Authorization: `Bearer ${adminToken}`,
          },
        }
      );

      if (documentsResponse.ok()) {
        const documentsData = await documentsResponse.json();

        // Delete test documents
        for (const document of documentsData.documents || []) {
          if (
            document.filename.includes('e2e-test') ||
            document.filename.includes('playwright-test')
          ) {
            const deleteResponse = await request.delete(
              `http://localhost:8000/documents/${document.id}`,
              {
                headers: {
                  Authorization: `Bearer ${adminToken}`,
                },
              }
            );

            if (deleteResponse.ok()) {
              console.log(`✅ Cleaned up test document: ${document.filename}`);
            }
          }
        }
      }
    }
  } catch (error) {
    console.log('⚠️  Could not cleanup test files:', error);
  }
}
