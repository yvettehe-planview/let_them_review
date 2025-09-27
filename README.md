# let_them_review
Our project integrates two AI bots into GitHub's code review process: ReviewBot and FixBot. ReviewBot analyzes PRs, summarizes changes, and suggests code improvements, while FixBot automatically implements these suggestions pending human approval.

## How to use it?
# GitHub Actions - Automated Code Review

This .github directory sets up GitHub Actions workflows that integrate two AI bots from the `let_them_review` repository. Real exmpale: https://github.com/Yarui-planview/Demo-project-for-hackathon-planview

## Workflows

### 1. `pr-review-bot.yml`  
- **Trigger**: Pull requests open
- **Purpose**: Alternative workflow with same functionality
- **Action**: Runs `run_review.py` from the `let_them_review` repository

### 2. `automated-code-review.yml`
- **Trigger**: Pull requests (opened, synchronized, reopened)
- **Purpose**: Main workflow for automated code review
- **Action**: Runs `bot_trigger.py` from the `let_them_review` repository

## Required Secrets

Set up these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

### Required:
- `GIT_TOKEN` - Fine-grained personal access token with repository-specific permissions:
   - Actions: Read
   - Contents: Write
   - Issues: Write, 
   - Metadata: Read, 
   - Pull requests: Write
   
   Create at GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens, scope to this repository only.

- `FALCON_API_KEY` : Your Falconai API key (Me → Account → API keys)


## Simple Setup

1. **Add Secrets** :

   Set up these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

- `GIT_TOKEN` - Fine-grained personal access token with repository-specific permissions:
   - Actions: Read
   - Contents: Write
   - Issues: Write, 
   - Metadata: Read, 
   - Pull requests: Write
   
   Create at GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens, scope to this repository only.

- `FALCON_API_KEY` : Your Falconai API key (Me → Account → API keys)

2. **Add the Workflows** - Copy the workflow files from .github/workflows/ to your repository's .github/workflows/ directory

3. **Create a PR** - The review bot will automatically run!
