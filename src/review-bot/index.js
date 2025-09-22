/**
 * ReviewBot entry point
 * Orchestrates the AI-powered code review process
 */

const ReviewBot = require('./reviewBot');

async function main() {
  try {
    console.log('🚀 Starting ReviewBot...');
    
    const reviewBot = new ReviewBot();
    await reviewBot.reviewPullRequest();
    
    console.log('✅ ReviewBot completed successfully');
    process.exit(0);
    
  } catch (error) {
    console.error('❌ ReviewBot failed:', error);
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