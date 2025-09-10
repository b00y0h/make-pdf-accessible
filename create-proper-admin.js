// Create admin user using BetterAuth's proper registration system
const { default: fetch } = require("node-fetch");

async function createProperAdmin() {
    try {
        console.log("🔄 Creating admin user via BetterAuth registration...");
        
        // Now register the admin user through BetterAuth's API
        console.log("📝 Registering admin user through BetterAuth...");
        const signupResponse = await fetch("http://localhost:3001/api/auth/sign-up/email", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                email: "admin@accesspdf.com",
                password: "admin123ssggtg$23543DDEFFG32hf",
                name: "admin"
            }),
        });

        console.log("Sign-up status:", signupResponse.status);
        
        if (!signupResponse.ok) {
            const errorText = await signupResponse.text();
            console.log("Sign-up error:", errorText);
            return;
        }

        const signupData = await signupResponse.json();
        console.log("✅ Admin user registered:", signupData.user);
        
        console.log("👑 User created, will set admin role manually via database if needed");
        
        // Test login
        console.log("🔐 Testing admin login...");
        const loginResponse = await fetch("http://localhost:3001/api/auth/sign-in/email", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                email: "admin@accesspdf.com",
                password: "admin123ssggtg$23543DDEFFG32hf",
            }),
        });

        console.log("Login status:", loginResponse.status);
        
        if (loginResponse.ok) {
            console.log("✅ Admin login successful!");
            const cookies = loginResponse.headers.get("set-cookie") || "";
            console.log("🍪 Session cookie:", cookies);
        } else {
            const errorText = await loginResponse.text();
            console.log("❌ Login failed:", errorText);
        }

    } catch (error) {
        console.error("❌ Failed to create admin user:", error.message);
    }
}

createProperAdmin();