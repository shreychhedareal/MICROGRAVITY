// This file is a CommonJS module, so we use 'require'.
const dotenv = require('dotenv');
const path = require('path');

/**
 * In a .cjs file, __dirname is the absolute path to the directory containing the file.
 * We resolve the path to the .env file located in the parent directory (server/).
 * This ensures the environment variables are loaded before any other application code runs.
 */
const envPath = path.resolve(__dirname, '..', '.env');
console.log(`[config] Attempting to load environment variables from: ${envPath}`);

const result = dotenv.config({ path: envPath, debug: true });

if (result.error) {
  console.error('🔴 [config] Error loading .env file:', result.error);
} else if (!result.parsed || Object.keys(result.parsed).length === 0) {
    console.warn('🟡 [config] .env file was found and read, but it appears to be empty or malformed.');
    console.log('[config] Raw parsed content:', result.parsed);
}
else {
  console.log('🟢 [config] Successfully parsed .env file.');
  // For security, we only log the keys, not the values.
  console.log('[config] Found keys:', Object.keys(result.parsed));
}

// Final check to see if the key is loaded into the current process
if(process.env.GEMINI_API_KEY) {
    console.log('✅ [config] GEMINI_API_KEY is available in process.env.');
} else {
    console.error('❌ [config] GEMINI_API_KEY was NOT found in process.env after loading.');
} 