# Let Them Review 🤖⚔️🤖

An AI-enhanced code review system that integrates two powerful bots into GitHub's code review process using Claude's MCP (Message Code Protocol) for intelligent code analysis and automated fixes.

## 🎯 Overview

**ReviewBot** analyzes pull requests, summarizes changes, and suggests code improvements using advanced AI analysis, while **FixBot** automatically implements these suggestions with human approval. What makes this workflow unique is watching these two AI agents collaborate (and sometimes battle) with each other to continuously improve code quality.

## ✨ Features

### 🔍 ReviewBot
- **Intelligent Code Analysis**: Deep code review using Claude's MCP protocol
- **Multi-Language Support**: Analyzes JavaScript, TypeScript, Python, Java, Go, Rust, C++, C#, and more
- **Comprehensive Feedback**: Identifies bugs, security issues, performance problems, and style violations
- **Severity Classification**: Categorizes issues by severity (high, medium, low) and type
- **Rich Comments**: Posts detailed, actionable feedback directly on pull requests

### 🔧 FixBot
- **Automated Fixes**: Implements suggested improvements automatically
- **Smart Targeting**: Responds to `@fixbot` mentions for specific fix requests
- **Safe Operations**: Only applies low-risk fixes automatically (style, performance, refactoring)
- **Human Oversight**: Requires approval for high-severity changes
- **Multiple Languages**: Supports the same languages as ReviewBot

### 🌐 Claude MCP Integration
- **Protocol Version**: Implements MCP 2024-11-05
- **Advanced AI**: Leverages Claude-3.5-Sonnet for intelligent analysis
- **Structured Communication**: Uses MCP for reliable AI-to-system communication
- **Extensible**: Built for future AI capabilities and improvements

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- GitHub repository with Actions enabled
- Anthropic Claude API access
- GitHub Personal Access Token

### Installation

1. **Clone and Setup**
   ```bash
   git clone https://github.com/yvettehe-planview/let_them_review.git
   cd let_them_review
   npm install
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Set GitHub Secrets**
   Add these secrets to your repository:
   - `CLAUDE_API_KEY`: Your Anthropic Claude API key
   - `GITHUB_TOKEN`: Automatically provided by GitHub Actions

### Usage

The system automatically activates when:

#### 🔍 ReviewBot Triggers
- Pull request opened
- Pull request updated
- Pull request reopened

#### 🔧 FixBot Triggers
- Comment contains `@fixbot`
- PR review contains `@fixbot`

#### Example Commands
```bash
# Request all automated fixes
@fixbot apply all

# Request specific fixes
@fixbot apply

# Request targeted fixes
@fixbot fix performance issues
```

## 📁 Project Structure

```
let_them_review/
├── .github/workflows/       # GitHub Actions workflows
│   ├── review-bot.yml      # ReviewBot automation
│   └── fix-bot.yml         # FixBot automation
├── src/
│   ├── config/             # Configuration management
│   ├── review-bot/         # ReviewBot implementation
│   ├── fix-bot/            # FixBot implementation
│   ├── mcp/                # Claude MCP client
│   ├── utils/              # Shared utilities
│   └── index.js            # Main entry point
├── package.json            # Dependencies and scripts
└── README.md              # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_TOKEN` | GitHub API access token | ✅ |
| `CLAUDE_API_KEY` | Anthropic Claude API key | ✅ |
| `PR_NUMBER` | Pull request number (auto-set) | ✅ |
| `REPO_OWNER` | Repository owner (auto-set) | ✅ |
| `REPO_NAME` | Repository name (auto-set) | ✅ |

### ReviewBot Settings

```javascript
reviewBot: {
  enabled: true,
  maxFilesPerReview: 50,
  excludePatterns: [
    'node_modules/**',
    'dist/**',
    '*.min.js'
  ]
}
```

### FixBot Settings

```javascript
fixBot: {
  enabled: true,
  maxChangesPerRun: 10,
  supportedLanguages: [
    'javascript', 'typescript', 'python',
    'java', 'go', 'rust', 'cpp', 'csharp'
  ]
}
```

## 🎨 Example Workflow

1. **Developer** opens a pull request
2. **ReviewBot** automatically analyzes the code
3. **ReviewBot** posts comprehensive review with issues and suggestions
4. **Developer** or **Reviewer** comments `@fixbot apply`
5. **FixBot** implements safe, automated fixes
6. **FixBot** commits changes back to the PR
7. **Human reviewers** approve the enhanced code

## 🛡️ Security & Safety

- **Limited Scope**: FixBot only applies low-risk fixes automatically
- **Human Approval**: High-severity issues require manual review
- **Audit Trail**: All changes are committed with clear attribution
- **Configurable**: Admins can control what types of fixes are allowed
- **Fail-Safe**: System gracefully handles API failures and errors

## 🔍 Supported Issue Types

### ReviewBot Analysis
- 🐛 **Bugs**: Logic errors, null pointer issues, type mismatches
- 🔒 **Security**: Vulnerabilities, injection risks, sensitive data exposure
- ⚡ **Performance**: Inefficient algorithms, memory leaks, bottlenecks
- 🎨 **Style**: Code formatting, naming conventions, best practices
- ♻️ **Refactoring**: Code structure improvements, duplication removal
- 🏗️ **Architecture**: Design pattern violations, coupling issues

### FixBot Capabilities
- ✅ **Auto-Fix**: Style, formatting, simple performance optimizations
- ⚠️ **Manual Review**: Security issues, complex logic changes
- 🔄 **Refactoring**: Structure improvements with human approval

## 📊 AI Technology Stack

- **Claude-3.5-Sonnet**: Advanced language model for code analysis
- **MCP Protocol**: Message Code Protocol for structured AI communication
- **GitHub API**: Integration with GitHub's review system
- **Node.js**: Runtime environment for bot execution
- **GitHub Actions**: Automated workflow execution

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with the ReviewBot and FixBot
5. Submit a pull request (and watch the bots review it!)

## 📜 License

MIT License - see LICENSE file for details

## 🆘 Support

- 📧 **Issues**: Use GitHub Issues for bug reports
- 💬 **Discussions**: GitHub Discussions for questions
- 📖 **Documentation**: Check the wiki for detailed guides

---

**🤖 Built with AI, for developers, by Planview**

*Let ReviewBot and FixBot handle the tedious parts of code review so you can focus on the creative aspects of software development.*
