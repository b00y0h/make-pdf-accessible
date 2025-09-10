import { betterAuth } from "better-auth"
import { username } from "better-auth/plugins"
import { Pool } from "pg"

export const auth = betterAuth({
  database: new Pool({
    connectionString: process.env.AUTH_DATABASE_URL || "postgresql://postgres:password@localhost:5433/better_auth",
  }),
  baseURL: process.env.BETTER_AUTH_URL || "http://localhost:3001",
  secret: process.env.BETTER_AUTH_SECRET || "your-better-auth-secret-change-in-production",
  trustedOrigins: ["http://localhost:3001", "http://dashboard:3001"],
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false,
  },
  plugins: [
    username({
      required: false,
    }),
  ],
  user: {
    additionalFields: {
      role: {
        type: "string",
        required: false,
        defaultValue: "user",
      },
      orgId: {
        type: "string", 
        required: false,
      },
    },
  },
});