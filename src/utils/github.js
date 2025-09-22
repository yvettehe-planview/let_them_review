/**
 * GitHub API utilities for interacting with repositories, PRs, and issues
 */

const { Octokit } = require('@octokit/rest');
const config = require('../config/config');

class GitHubClient {
  constructor() {
    if (!config.github.token) {
      throw new Error('GITHUB_TOKEN environment variable is required');
    }
    
    this.octokit = new Octokit({
      auth: config.github.token,
    });
    
    this.owner = config.github.owner;
    this.repo = config.github.repo;
  }

  /**
   * Get pull request details
   */
  async getPullRequest(prNumber) {
    try {
      const { data } = await this.octokit.rest.pulls.get({
        owner: this.owner,
        repo: this.repo,
        pull_number: prNumber,
      });
      
      return data;
    } catch (error) {
      console.error('Error fetching pull request:', error);
      throw error;
    }
  }

  /**
   * Get files changed in a pull request
   */
  async getPullRequestFiles(prNumber) {
    try {
      const { data } = await this.octokit.rest.pulls.listFiles({
        owner: this.owner,
        repo: this.repo,
        pull_number: prNumber,
      });
      
      return data;
    } catch (error) {
      console.error('Error fetching PR files:', error);
      throw error;
    }
  }

  /**
   * Get file content from repository
   */
  async getFileContent(path, ref = 'main') {
    try {
      const { data } = await this.octokit.rest.repos.getContent({
        owner: this.owner,
        repo: this.repo,
        path: path,
        ref: ref,
      });
      
      if (data.encoding === 'base64') {
        return Buffer.from(data.content, 'base64').toString('utf-8');
      }
      
      return data.content;
    } catch (error) {
      console.error(`Error fetching file content for ${path}:`, error);
      return null;
    }
  }

  /**
   * Create a review comment on a pull request
   */
  async createReviewComment(prNumber, body, commitSha, path, line) {
    try {
      const { data } = await this.octokit.rest.pulls.createReviewComment({
        owner: this.owner,
        repo: this.repo,
        pull_number: prNumber,
        body: body,
        commit_id: commitSha,
        path: path,
        line: line,
      });
      
      return data;
    } catch (error) {
      console.error('Error creating review comment:', error);
      throw error;
    }
  }

  /**
   * Create a pull request review
   */
  async createReview(prNumber, body, event = 'COMMENT') {
    try {
      const { data } = await this.octokit.rest.pulls.createReview({
        owner: this.owner,
        repo: this.repo,
        pull_number: prNumber,
        body: body,
        event: event,
      });
      
      return data;
    } catch (error) {
      console.error('Error creating review:', error);
      throw error;
    }
  }

  /**
   * Add comment to an issue/PR
   */
  async createComment(issueNumber, body) {
    try {
      const { data } = await this.octokit.rest.issues.createComment({
        owner: this.owner,
        repo: this.repo,
        issue_number: issueNumber,
        body: body,
      });
      
      return data;
    } catch (error) {
      console.error('Error creating comment:', error);
      throw error;
    }
  }

  /**
   * Update file content in repository
   */
  async updateFile(path, content, message, sha, branch = 'main') {
    try {
      const { data } = await this.octokit.rest.repos.createOrUpdateFileContents({
        owner: this.owner,
        repo: this.repo,
        path: path,
        message: message,
        content: Buffer.from(content).toString('base64'),
        sha: sha,
        branch: branch,
      });
      
      return data;
    } catch (error) {
      console.error('Error updating file:', error);
      throw error;
    }
  }

  /**
   * Get repository information
   */
  async getRepository() {
    try {
      const { data } = await this.octokit.rest.repos.get({
        owner: this.owner,
        repo: this.repo,
      });
      
      return data;
    } catch (error) {
      console.error('Error fetching repository:', error);
      throw error;
    }
  }

  /**
   * Get commit information
   */
  async getCommit(sha) {
    try {
      const { data } = await this.octokit.rest.repos.getCommit({
        owner: this.owner,
        repo: this.repo,
        ref: sha,
      });
      
      return data;
    } catch (error) {
      console.error('Error fetching commit:', error);
      throw error;
    }
  }

  /**
   * Filter files based on exclude patterns
   */
  filterFiles(files) {
    const excludePatterns = config.reviewBot.excludePatterns;
    
    return files.filter(file => {
      return !excludePatterns.some(pattern => {
        const regex = new RegExp(pattern.replace(/\*\*/g, '.*').replace(/\*/g, '[^/]*'));
        return regex.test(file.filename);
      });
    });
  }

  /**
   * Detect file language based on extension
   */
  detectLanguage(filename) {
    const extension = filename.split('.').pop()?.toLowerCase();
    
    const languageMap = {
      'js': 'javascript',
      'jsx': 'javascript',
      'ts': 'typescript',
      'tsx': 'typescript',
      'py': 'python',
      'java': 'java',
      'go': 'go',
      'rs': 'rust',
      'cpp': 'cpp',
      'cc': 'cpp',
      'cxx': 'cpp',
      'c': 'c',
      'cs': 'csharp',
      'php': 'php',
      'rb': 'ruby',
      'swift': 'swift',
      'kt': 'kotlin',
      'scala': 'scala',
      'sh': 'bash',
      'sql': 'sql',
      'html': 'html',
      'css': 'css',
      'scss': 'scss',
      'sass': 'sass',
      'json': 'json',
      'yaml': 'yaml',
      'yml': 'yaml',
      'xml': 'xml',
      'md': 'markdown',
    };
    
    return languageMap[extension] || 'text';
  }
}

module.exports = GitHubClient;