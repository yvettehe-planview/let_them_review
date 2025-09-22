/**
 * Configuration for AI-enhanced code review system
 */

const config = {
  github: {
    token: process.env.GITHUB_TOKEN,
    apiUrl: 'https://api.github.com',
    owner: process.env.REPO_OWNER,
    repo: process.env.REPO_NAME,
  },
  
  claude: {
    apiKey: process.env.CLAUDE_API_KEY,
    model: 'claude-3-5-sonnet-20241022',
    maxTokens: 4000,
  },
  
  reviewBot: {
    enabled: true,
    maxFilesPerReview: 50,
    excludePatterns: [
      'node_modules/**',
      'dist/**',
      'build/**',
      '*.min.js',
      '*.min.css',
      'package-lock.json',
      'yarn.lock'
    ],
    reviewPrompts: {
      summary: 'Analyze this pull request and provide a comprehensive summary of changes, potential issues, and recommendations.',
      codeQuality: 'Review the code quality, identify potential bugs, security issues, and suggest improvements.',
      performance: 'Analyze performance implications and suggest optimizations.',
      architecture: 'Review architectural decisions and design patterns used.'
    }
  },
  
  fixBot: {
    enabled: true,
    autoApprovalRequired: true,
    maxChangesPerRun: 10,
    supportedLanguages: [
      'javascript',
      'typescript',
      'python',
      'java',
      'go',
      'rust',
      'cpp',
      'csharp'
    ],
    fixTypes: {
      bugs: 'Fix identified bugs and logical errors',
      performance: 'Apply performance optimizations',
      style: 'Fix code style and formatting issues',
      security: 'Address security vulnerabilities',
      refactor: 'Improve code structure and readability'
    }
  },
  
  mcp: {
    protocol: '2024-11-05',
    capabilities: {
      tools: true,
      resources: true,
      prompts: true,
      logging: true
    }
  }
};

module.exports = config;