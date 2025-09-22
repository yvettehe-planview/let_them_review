# Setup Guide

## Prerequisites

1. **Node.js 18+**: Ensure you have Node.js version 18 or higher installed
2. **GitHub Repository**: Repository with GitHub Actions enabled
3. **Claude API Access**: Anthropic Claude API key
4. **GitHub Token**: Personal access token with repository permissions

## Step-by-Step Setup

### 1. Repository Setup

1. Clone or fork this repository
2. Install dependencies:
   ```bash
   npm install
   ```

### 2. Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```env
   GITHUB_TOKEN=your_github_token_here
   CLAUDE_API_KEY=your_claude_api_key_here
   ```

### 3. GitHub Secrets Configuration

Add the following secrets to your GitHub repository:

1. Go to `Settings > Secrets and variables > Actions`
2. Add repository secrets:
   - `CLAUDE_API_KEY`: Your Anthropic Claude API key

Note: `GITHUB_TOKEN` is automatically provided by GitHub Actions.

### 4. API Key Setup

#### Claude API Key
1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Create an account or sign in
3. Generate an API key
4. Add it to your GitHub repository secrets as `CLAUDE_API_KEY`

#### GitHub Token (if needed for local testing)
1. Go to GitHub Settings > Developer settings > Personal access tokens
2. Generate a new token with `repo` permissions
3. Add it to your `.env` file (never commit this file)

### 5. Testing the Setup

1. Test the system locally:
   ```bash
   node src/index.js info
   ```

2. Run the test suite:
   ```bash
   npm test
   ```

3. Check code quality:
   ```bash
   npm run lint
   ```

### 6. Workflow Activation

The bots activate automatically when:

- **ReviewBot**: PR opened, updated, or reopened
- **FixBot**: Comment contains `@fixbot` or PR review contains `@fixbot`

### 7. First Use

1. Create a test pull request
2. ReviewBot will automatically analyze the code
3. Try commenting `@fixbot apply` to test FixBot
4. Review the generated comments and fixes

## Troubleshooting

### Common Issues

1. **"CLAUDE_API_KEY not found"**
   - Ensure the secret is added to GitHub repository
   - For local testing, check your `.env` file

2. **"GITHUB_TOKEN not found"**
   - This is automatically provided in GitHub Actions
   - For local testing, add it to your `.env` file

3. **Workflow not triggering**
   - Check that GitHub Actions are enabled in repository settings
   - Verify the workflow files are in `.github/workflows/`

4. **Bot not responding**
   - Check the Actions tab for error logs
   - Verify API keys are correctly configured

### Health Check

Run the health check command to verify all components:

```bash
node src/index.js health
```

This will test:
- Configuration loading
- GitHub API connectivity (if token provided)
- Claude MCP connection (if API key provided)

## Next Steps

1. Customize the configuration in `src/config/config.js`
2. Adjust the workflow triggers in `.github/workflows/`
3. Monitor the bots in action through GitHub Actions logs
4. Review and refine the AI prompts as needed

## Support

- Review the main README.md for detailed usage information
- Check the GitHub Issues for known problems
- Use GitHub Discussions for questions and community support