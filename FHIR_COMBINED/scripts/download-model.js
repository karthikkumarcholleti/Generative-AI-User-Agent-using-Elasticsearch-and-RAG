#!/usr/bin/env node

/**
 * Download LLM Model Script
 * 
 * Downloads the Llama 3.1 8B model from HuggingFace if not already present.
 * Requires: huggingface-cli to be installed and logged in
 * 
 * Usage: node scripts/download-model.js
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const MODEL_NAME = 'meta-llama/Llama-3.1-8B-Instruct';
const MODEL_DIR = path.join(__dirname, '../FHIR_LLM_UA/models/llama31-8b-bnb4');

console.log('📦 LLM Model Download Script\n');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

// Check if model already exists
if (fs.existsSync(MODEL_DIR) && fs.readdirSync(MODEL_DIR).length > 0) {
    console.log('✅ Model already exists at:', MODEL_DIR);
    console.log('   Skipping download.\n');
    process.exit(0);
}

console.log('📥 Model not found. Starting download...\n');
console.log('⚠️  This will download ~5.4GB. Make sure you have:');
console.log('   1. HuggingFace account');
console.log('   2. Access to Llama models (request access at https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct)');
console.log('   3. Logged in: huggingface-cli login\n');

// Check if huggingface-cli is installed
try {
    execSync('huggingface-cli --version', { stdio: 'ignore' });
} catch (error) {
    console.error('❌ Error: huggingface-cli is not installed.');
    console.error('   Install it with: pip install huggingface-hub[cli]');
    console.error('   Or: pip install huggingface-cli\n');
    process.exit(1);
}

// Check if user is logged in
try {
    execSync('huggingface-cli whoami', { stdio: 'ignore' });
} catch (error) {
    console.error('❌ Error: Not logged in to HuggingFace.');
    console.error('   Run: huggingface-cli login');
    console.error('   Then enter your HuggingFace token.\n');
    process.exit(1);
}

// Create model directory if it doesn't exist
if (!fs.existsSync(MODEL_DIR)) {
    fs.mkdirSync(MODEL_DIR, { recursive: true });
    console.log('📁 Created model directory:', MODEL_DIR, '\n');
}

// Download model
console.log('⬇️  Downloading model from HuggingFace...');
console.log('   Model:', MODEL_NAME);
console.log('   Destination:', MODEL_DIR);
console.log('   This may take 10-30 minutes depending on your internet speed...\n');

try {
    execSync(
        `huggingface-cli download ${MODEL_NAME} --local-dir "${MODEL_DIR}"`,
        { stdio: 'inherit' }
    );
    console.log('\n✅ Model downloaded successfully!\n');
    console.log('📝 Next steps:');
    console.log('   1. Make sure your .env file points to:', MODEL_DIR);
    console.log('   2. Run: npm run dev\n');
} catch (error) {
    console.error('\n❌ Error downloading model.');
    console.error('   Please check:');
    console.error('   1. You have access to Llama models on HuggingFace');
    console.error('   2. You are logged in: huggingface-cli whoami');
    console.error('   3. You have enough disk space (~6GB free)\n');
    process.exit(1);
}

