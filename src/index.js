/**
 * Main entry point for the AI-enhanced code review system
 * Coordinates ReviewBot and FixBot functionality
 */

const config = require('./config/config');
const ReviewBot = require('./review-bot/reviewBot');
const FixBot = require('./fix-bot/fixBot');

class LetThemReview {
  constructor() {
    this.config = config;
  }

  /**
   * Run ReviewBot for code analysis
   */
  async runReviewBot() {
    try {
      console.log('🤖 Starting ReviewBot...');
      const reviewBot = new ReviewBot();
      await reviewBot.reviewPullRequest();
      console.log('✅ ReviewBot completed');
    } catch (error) {
      console.error('❌ ReviewBot failed:', error);
      throw error;
    }
  }

  /**
   * Run FixBot for automated fixes
   */
  async runFixBot() {
    try {
      console.log('🔧 Starting FixBot...');
      const fixBot = new FixBot();
      await fixBot.processFixRequest();
      console.log('✅ FixBot completed');
    } catch (error) {
      console.error('❌ FixBot failed:', error);
      throw error;
    }
  }

  /**
   * Health check for the system
   */
  async healthCheck() {
    try {
      console.log('🏥 Running system health check...');
      
      // Check configuration
      if (!config.github.token) {
        throw new Error('GitHub token not configured');
      }
      
      if (!config.claude.apiKey) {
        throw new Error('Claude API key not configured');
      }
      
      // Test GitHub API connection
      const GitHubClient = require('./utils/github');
      const githubClient = new GitHubClient();
      await githubClient.getRepository();
      
      // Test Claude MCP connection
      const MCPClient = require('./mcp/client');
      const mcpClient = new MCPClient();
      const isHealthy = await mcpClient.healthCheck();
      
      if (!isHealthy) {
        throw new Error('Claude MCP connection failed');
      }
      
      console.log('✅ System health check passed');
      return true;
      
    } catch (error) {
      console.error('❌ System health check failed:', error);
      return false;
    }
  }

  /**
   * Display system information
   */
  getSystemInfo() {
    return {
      name: 'let-them-review',
      version: '1.0.0',
      description: 'AI-enhanced code review system with ReviewBot and FixBot',
      features: {
        reviewBot: {
          enabled: config.reviewBot.enabled,
          maxFiles: config.reviewBot.maxFilesPerReview,
          supportedLanguages: 'All text-based languages'
        },
        fixBot: {
          enabled: config.fixBot.enabled,
          maxChanges: config.fixBot.maxChangesPerRun,
          supportedLanguages: config.fixBot.supportedLanguages
        },
        mcp: {
          protocol: config.mcp.protocol,
          model: config.claude.model
        }
      }
    };
  }
}

module.exports = LetThemReview;

async function runCommand() {
  try {
    const command = process.argv[2];
    const system = new LetThemReview();
    
    switch (command) {
    case 'review':
      await system.runReviewBot();
      break;
    case 'fix':
      await system.runFixBot();
      break;
    case 'health': {
      const isHealthy = await system.healthCheck();
      process.exit(isHealthy ? 0 : 1);
      break;
    }
    case 'info':
      console.log(JSON.stringify(system.getSystemInfo(), null, 2));
      break;
    default:
      console.log('Available commands: review, fix, health, info');
      console.log('Usage: node src/index.js <command>');
      break;
    }
  } catch (error) {
    console.error('Command failed:', error);
    process.exit(1);
  }
}

// CLI interface
if (require.main === module) {
  const command = process.argv[2];
  const system = new LetThemReview();

  async function runCommand() {
    try {
      switch (command) {
      case 'review':
        await system.runReviewBot();
        break;
      case 'fix':
        await system.runFixBot();
        break;
      case 'health':
        const isHealthy = await system.healthCheck();
        process.exit(isHealthy ? 0 : 1);
        break;
      case 'info':
        console.log(JSON.stringify(system.getSystemInfo(), null, 2));
        break;
      default:
        console.log('Available commands: review, fix, health, info');
        console.log('Usage: node src/index.js <command>');
        break;
      }
    } catch (error) {
      console.error('Command failed:', error);
      process.exit(1);
    }
  }

  runCommand();
}