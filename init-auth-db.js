// Initialize BetterAuth database with admin user
const Database = require('better-sqlite3');
const bcrypt = require('bcryptjs');

// Connect to the shared database
const db = new Database('./auth_data/sqlite.db');

console.log('🔄 Initializing BetterAuth database...');

// Create user table
db.exec(`
  CREATE TABLE IF NOT EXISTS user (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    username TEXT,
    role TEXT DEFAULT 'user',
    orgId TEXT,
    emailVerified INTEGER DEFAULT 0,
    image TEXT,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
  );
`);

// Create session table
db.exec(`
  CREATE TABLE IF NOT EXISTS session (
    id TEXT PRIMARY KEY,
    userId TEXT NOT NULL,
    expiresAt DATETIME NOT NULL,
    token TEXT NOT NULL,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userId) REFERENCES user(id) ON DELETE CASCADE
  );
`);

// Create account table (for OAuth providers)
db.exec(`
  CREATE TABLE IF NOT EXISTS account (
    id TEXT PRIMARY KEY,
    userId TEXT NOT NULL,
    accountId TEXT NOT NULL,
    providerId TEXT NOT NULL,
    accessToken TEXT,
    refreshToken TEXT,
    idToken TEXT,
    accessTokenExpiresAt DATETIME,
    refreshTokenExpiresAt DATETIME,
    scope TEXT,
    password TEXT,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userId) REFERENCES user(id) ON DELETE CASCADE
  );
`);

// Create verification table
db.exec(`
  CREATE TABLE IF NOT EXISTS verification (
    id TEXT PRIMARY KEY,
    identifier TEXT NOT NULL,
    value TEXT NOT NULL,
    expiresAt DATETIME NOT NULL,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
  );
`);

console.log('✅ Database schema created');

// Hash the admin password
const adminEmail = 'admin@accesspdf.com';
const adminPassword = 'admin123ssggtg$23543DDEFFG32hf';
const hashedPassword = bcrypt.hashSync(adminPassword, 10);

// Generate admin user ID
const adminId = 'df34b00c-536b-4bab-807f-17ccee6a5345'; // Use same ID as before for consistency

// Insert admin user
const insertUser = db.prepare(`
  INSERT OR REPLACE INTO user (id, email, name, role, emailVerified, createdAt, updatedAt)
  VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
`);

insertUser.run(adminId, adminEmail, 'admin', 'admin', 1);

// Insert admin account with password
const insertAccount = db.prepare(`
  INSERT OR REPLACE INTO account (id, userId, accountId, providerId, password, createdAt, updatedAt)
  VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
`);

insertAccount.run(
  'admin-account-id',
  adminId,
  adminId,
  'credential',
  hashedPassword
);

console.log('✅ Admin user created:');
console.log(`   Email: ${adminEmail}`);
console.log(`   Role: admin`);

// Verify the user was created
const getUser = db.prepare(
  'SELECT id, email, name, role FROM user WHERE email = ?'
);
const user = getUser.get(adminEmail);
console.log('👤 Admin user data:', user);

db.close();
console.log('✅ Database initialization complete!');
