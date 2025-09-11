// Seed admin user using BetterAuth API
const fetch = require('node-fetch');

async function createAdminUser() {
  const adminData = {
    email: 'admin@example.com',
    password: 'admin123456', // 8+ characters required
    name: 'Admin User',
  };

  try {
    console.log('Creating admin user...');
    console.log(`Email: ${adminData.email}`);
    console.log(`Password: ${adminData.password}`);

    const response = await fetch(
      'http://localhost:3001/api/auth/sign-up/email',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(adminData),
      }
    );

    const result = await response.text();

    if (response.ok) {
      console.log('✅ Admin user created successfully!');
      console.log('Response:', result);

      // Now update the user role to admin in the database
      console.log('\n🔧 Setting admin role...');
      const Database = require('better-sqlite3');
      const db = new Database('./sqlite.db');

      const updateRole = db.prepare('UPDATE user SET role = ? WHERE email = ?');
      updateRole.run('admin', adminData.email);

      console.log('✅ Admin role set successfully!');
      console.log('\n🎉 Admin user ready:');
      console.log(`📧 Email: ${adminData.email}`);
      console.log(`🔐 Password: ${adminData.password}`);

      db.close();
    } else {
      console.log('❌ Failed to create user');
      console.log('Status:', response.status);
      console.log('Response:', result);
    }
  } catch (error) {
    console.error('❌ Error creating admin user:', error);
  }
}

createAdminUser();
