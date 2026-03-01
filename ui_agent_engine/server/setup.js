#!/usr/bin/env node

/**
 * Setup script for Spatial Understanding API Server
 * Helps configure environment variables and API keys
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import readline from 'readline';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function question(prompt) {
  return new Promise((resolve) => {
    rl.question(prompt, resolve);
  });
}

async function setup() {
  console.log('🚀 Spatial Understanding API Server Setup');
  console.log('=========================================\n');

  console.log('This script will help you configure your environment variables.\n');

  // Check if .env already exists
  const envPath = path.join(__dirname, '.env');
  const envExamplePath = path.join(__dirname, 'env.example');
  
  if (fs.existsSync(envPath)) {
    console.log('⚠️  .env file already exists!');
    const overwrite = await question('Do you want to overwrite it? (y/N): ');
    if (overwrite.toLowerCase() !== 'y' && overwrite.toLowerCase() !== 'yes') {
      console.log('Setup cancelled.');
      rl.close();
      return;
    }
  }

  console.log('\n📋 Please provide the following information:\n');

  // Get Gemini API Key
  console.log('1. Google Gemini API Key');
  console.log('   Get your API key from: https://aistudio.google.com/app/apikey');
  const geminiApiKey = await question('   Enter your Gemini API Key: ');

  if (!geminiApiKey.trim()) {
    console.log('❌ Gemini API Key is required!');
    rl.close();
    return;
  }

  // Get other optional configurations
  console.log('\n2. Server Configuration (optional, press Enter for defaults)');
  
  const port = await question('   Server Port (default: 3001): ') || '3001';
  const nodeEnv = await question('   Environment (development/production, default: development): ') || 'development';
  
  console.log('\n3. Rate Limiting Configuration (optional)');
  const rateLimitMax = await question('   Max requests per window (default: 100): ') || '100';
  const rateLimitWindow = await question('   Rate limit window in minutes (default: 15): ') || '15';
  
  console.log('\n4. CORS Configuration (optional)');
  const allowedOrigins = await question('   Allowed origins (comma-separated, default: localhost:3000,localhost:3001,localhost:5173): ') 
    || 'http://localhost:3000,http://localhost:3001,http://localhost:5173';

  // Create .env content
  const envContent = `# Spatial Understanding API Server Configuration
# Generated on ${new Date().toISOString()}

# Google Gemini API Configuration
GEMINI_API_KEY=${geminiApiKey}

# Server Configuration
PORT=${port}
NODE_ENV=${nodeEnv}

# Rate Limiting
RATE_LIMIT_MAX_REQUESTS=${rateLimitMax}
RATE_LIMIT_WINDOW_MS=${parseInt(rateLimitWindow) * 60 * 1000}

# CORS Configuration
ALLOWED_ORIGINS=${allowedOrigins}

# Logging Configuration
LOG_LEVEL=info
LOG_FORMAT=combined

# Security Configuration
TRUST_PROXY=false
`;

  try {
    fs.writeFileSync(envPath, envContent);
    console.log('\n✅ Configuration saved to .env file!');
    
    console.log('\n📝 Next steps:');
    console.log('1. Install dependencies: npm install');
    console.log('2. Start the server: npm start');
    console.log('3. Open test UI: http://localhost:' + port + '/test-ui.html');
    console.log('4. Test API health: http://localhost:' + port + '/api/health');
    
    console.log('\n🔗 Useful Links:');
    console.log('• API Documentation: http://localhost:' + port + '/');
    console.log('• Test UI: http://localhost:' + port + '/test-ui.html');
    console.log('• Health Check: http://localhost:' + port + '/api/health');
    console.log('• Models Info: http://localhost:' + port + '/api/models');
    
  } catch (error) {
    console.error('❌ Error creating .env file:', error.message);
  }

  rl.close();
}

// Handle Ctrl+C gracefully
rl.on('SIGINT', () => {
  console.log('\n\n⚠️  Setup cancelled by user.');
  process.exit(0);
});

setup().catch(console.error); 