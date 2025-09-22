/**
 * FixBot entry point
 * Orchestrates the automated code fixing process
 */

const FixBot = require('./fixBot');

async function main() {
  try {
    console.log('🚀 Starting FixBot...');
    
    const fixBot = new FixBot();
    await fixBot.processFixRequest();
    
    console.log('✅ FixBot completed successfully');
    process.exit(0);
    
  } catch (error) {
    console.error('❌ FixBot failed:', error);
    process.exit(1);
  }
}

// Handle unhandled rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  process.exit(1);
});

main();