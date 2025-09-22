/**
 * FixBot - Automated code fixing agent
 * Implements suggested fixes from ReviewBot using Claude MCP
 */

const MCPClient = require('../mcp/client');
const GitHubClient = require('../utils/github');
const config = require('../config/config');
const fs = require('fs').promises;
const path = require('path');

class FixBot {
  constructor() {
    this.mcpClient = new MCPClient();
    this.githubClient = new GitHubClient();
    this.prNumber = process.env.PR_NUMBER;
    this.commentBody = process.env.COMMENT_BODY || '';
    
    if (!this.prNumber) {
      throw new Error('PR_NUMBER environment variable is required');
    }
  }

  /**
   * Main entry point for processing fix requests
   */
  async processFixRequest() {
    try {
      console.log(`🤖 FixBot processing request for PR #${this.prNumber}`);
      
      // Initialize MCP connection
      await this.mcpClient.initialize();
      
      // Health check
      const isHealthy = await this.mcpClient.healthCheck();
      if (!isHealthy) {
        throw new Error('MCP connection health check failed');
      }
      
      // Parse the comment to understand what needs to be fixed
      const fixRequest = this.parseFixRequest(this.commentBody);
      
      if (!fixRequest.shouldFix) {
        console.log('No fix request found in comment');
        return;
      }
      
      console.log(`Fix request type: ${fixRequest.type}`);
      
      // Get PR details
      const pullRequest = await this.githubClient.getPullRequest(this.prNumber);
      
      // Process the fix based on request type
      if (fixRequest.type === 'specific') {
        await this.applySpecificFixes(fixRequest, pullRequest);
      } else if (fixRequest.type === 'general') {
        await this.applyGeneralFixes(pullRequest);
      }
      
      console.log('✅ FixBot processing complete');
      
    } catch (error) {
      console.error('❌ FixBot error:', error);
      await this.postErrorComment(error.message);
    }
  }

  /**
   * Parse the comment to extract fix request details
   */
  parseFixRequest(commentBody) {
    const normalizedComment = commentBody.toLowerCase();
    
    // Check if this is a fix request
    if (!normalizedComment.includes('@fixbot')) {
      return { shouldFix: false };
    }
    
    // Parse different types of fix requests
    if (normalizedComment.includes('apply') || normalizedComment.includes('fix')) {
      if (normalizedComment.includes('all')) {
        return {
          shouldFix: true,
          type: 'general',
          scope: 'all'
        };
      } else {
        return {
          shouldFix: true,
          type: 'specific',
          scope: 'targeted'
        };
      }
    }
    
    // Default to general fixes
    return {
      shouldFix: true,
      type: 'general',
      scope: 'suggested'
    };
  }

  /**
   * Apply specific fixes based on targeted issues
   */
  async applySpecificFixes(fixRequest, pullRequest) {
    try {
      console.log('Applying specific fixes...');
      
      // Get the specific issues from recent ReviewBot comments
      const issues = await this.extractIssuesFromComments();
      
      if (issues.length === 0) {
        await this.postFixComment('No specific issues found to fix. Please ensure ReviewBot has analyzed the PR first.');
        return;
      }
      
      console.log(`Found ${issues.length} issues to fix`);
      
      // Group issues by file
      const issuesByFile = this.groupIssuesByFile(issues);
      
      let fixedFiles = 0;
      let totalFixes = 0;
      
      for (const [filename, fileIssues] of Object.entries(issuesByFile)) {
        console.log(`Fixing ${fileIssues.length} issues in ${filename}`);
        
        const result = await this.fixFileIssues(filename, fileIssues, pullRequest);
        if (result.success) {
          fixedFiles++;
          totalFixes += result.fixesApplied;
        }
      }
      
      await this.postFixSummary(fixedFiles, totalFixes, Object.keys(issuesByFile).length);
      
    } catch (error) {
      console.error('Error applying specific fixes:', error);
      throw error;
    }
  }

  /**
   * Apply general fixes to all files in the PR
   */
  async applyGeneralFixes(pullRequest) {
    try {
      console.log('Applying general fixes...');
      
      // Get all changed files
      const files = await this.githubClient.getPullRequestFiles(this.prNumber);
      const filteredFiles = this.githubClient.filterFiles(files);
      
      console.log(`Analyzing ${filteredFiles.length} files for potential fixes`);
      
      let fixedFiles = 0;
      let totalFixes = 0;
      
      for (const file of filteredFiles.slice(0, config.fixBot.maxChangesPerRun)) {
        console.log(`Analyzing ${file.filename} for fixes...`);
        
        const result = await this.analyzeAndFixFile(file, pullRequest);
        if (result.success) {
          fixedFiles++;
          totalFixes += result.fixesApplied;
        }
      }
      
      await this.postFixSummary(fixedFiles, totalFixes, filteredFiles.length);
      
    } catch (error) {
      console.error('Error applying general fixes:', error);
      throw error;
    }
  }

  /**
   * Extract issues from recent ReviewBot comments
   */
  async extractIssuesFromComments() {
    try {
      // This is a simplified implementation
      // In a real scenario, you'd parse the actual ReviewBot comments
      // For now, we'll return mock issues for demonstration
      return [
        {
          filename: 'example.js',
          type: 'style',
          severity: 'low',
          line: 10,
          description: 'Missing semicolon',
          suggestion: 'Add semicolon at end of statement'
        }
      ];
    } catch (error) {
      console.error('Error extracting issues:', error);
      return [];
    }
  }

  /**
   * Group issues by file
   */
  groupIssuesByFile(issues) {
    return issues.reduce((groups, issue) => {
      const filename = issue.filename;
      if (!groups[filename]) {
        groups[filename] = [];
      }
      groups[filename].push(issue);
      return groups;
    }, {});
  }

  /**
   * Fix issues in a specific file
   */
  async fixFileIssues(filename, issues, pullRequest) {
    try {
      // Get current file content
      const currentContent = await this.getCurrentFileContent(filename);
      if (!currentContent) {
        console.log(`Could not read ${filename}, skipping`);
        return { success: false, fixesApplied: 0 };
      }
      
      // Detect language
      const language = this.githubClient.detectLanguage(filename);
      
      // Generate fixes using Claude MCP
      const context = {
        filename: filename,
        language: language,
        pullRequestContext: `PR #${pullRequest.number}: ${pullRequest.title}`,
      };
      
      const fixedContent = await this.mcpClient.generateFixes(issues, currentContent, context);
      
      if (!fixedContent || fixedContent === currentContent) {
        console.log(`No fixes generated for ${filename}`);
        return { success: false, fixesApplied: 0 };
      }
      
      // Write the fixed content
      await this.writeFileContent(filename, fixedContent);
      
      console.log(`✅ Applied fixes to ${filename}`);
      return { success: true, fixesApplied: issues.length };
      
    } catch (error) {
      console.error(`Error fixing ${filename}:`, error);
      return { success: false, fixesApplied: 0 };
    }
  }

  /**
   * Analyze and fix a file generally
   */
  async analyzeAndFixFile(file, pullRequest) {
    try {
      // Skip if file is too large
      if (file.additions + file.deletions > 500) {
        console.log(`Skipping ${file.filename} - too large for automated fixes`);
        return { success: false, fixesApplied: 0 };
      }
      
      // Get file content
      const content = await this.getCurrentFileContent(file.filename);
      if (!content) {
        return { success: false, fixesApplied: 0 };
      }
      
      // Detect language and check if supported
      const language = this.githubClient.detectLanguage(file.filename);
      if (!config.fixBot.supportedLanguages.includes(language)) {
        console.log(`Language ${language} not supported for ${file.filename}`);
        return { success: false, fixesApplied: 0 };
      }
      
      // Analyze the file first to identify issues
      const context = {
        filename: file.filename,
        language: language,
        pullRequestContext: `PR #${pullRequest.number}: ${pullRequest.title}`,
      };
      
      const analysis = await this.mcpClient.analyzeCode(content, context);
      
      if (!analysis.issues || analysis.issues.length === 0) {
        console.log(`No issues found in ${file.filename}`);
        return { success: false, fixesApplied: 0 };
      }
      
      // Filter issues that FixBot should handle
      const fixableIssues = analysis.issues.filter(issue => 
        ['style', 'performance', 'refactor'].includes(issue.type) &&
        issue.severity !== 'high' // Don't auto-fix high severity issues
      );
      
      if (fixableIssues.length === 0) {
        console.log(`No auto-fixable issues in ${file.filename}`);
        return { success: false, fixesApplied: 0 };
      }
      
      // Generate and apply fixes
      const fixedContent = await this.mcpClient.generateFixes(fixableIssues, content, context);
      
      if (!fixedContent || fixedContent === content) {
        console.log(`No fixes generated for ${file.filename}`);
        return { success: false, fixesApplied: 0 };
      }
      
      // Write the fixed content
      await this.writeFileContent(file.filename, fixedContent);
      
      console.log(`✅ Applied ${fixableIssues.length} fixes to ${file.filename}`);
      return { success: true, fixesApplied: fixableIssues.length };
      
    } catch (error) {
      console.error(`Error analyzing/fixing ${file.filename}:`, error);
      return { success: false, fixesApplied: 0 };
    }
  }

  /**
   * Get current file content from local filesystem
   */
  async getCurrentFileContent(filename) {
    try {
      const filePath = path.join(process.cwd(), filename);
      const content = await fs.readFile(filePath, 'utf-8');
      return content;
    } catch (error) {
      console.error(`Error reading ${filename}:`, error);
      return null;
    }
  }

  /**
   * Write fixed content to file
   */
  async writeFileContent(filename, content) {
    try {
      const filePath = path.join(process.cwd(), filename);
      await fs.writeFile(filePath, content, 'utf-8');
    } catch (error) {
      console.error(`Error writing ${filename}:`, error);
      throw error;
    }
  }

  /**
   * Post fix summary comment
   */
  async postFixSummary(fixedFiles, totalFixes, totalFiles) {
    const comment = '## 🔧 FixBot Results\n\n' +
      '✅ **Automated fixes applied successfully!**\n\n' +
      '### 📊 Summary\n' +
      `- **Files processed:** ${totalFiles}\n` +
      `- **Files modified:** ${fixedFiles}\n` +
      `- **Total fixes applied:** ${totalFixes}\n\n` +
      '### 🎯 Fix Types Applied\n' +
      '- Code style improvements\n' +
      '- Performance optimizations\n' +
      '- Refactoring suggestions\n\n' +
      '---\n' +
      '🤖 *Changes have been committed automatically. Please review the modifications before merging.*';

    try {
      await this.githubClient.createComment(this.prNumber, comment);
    } catch (error) {
      console.error('Error posting fix summary:', error);
    }
  }

  /**
   * Post fix comment
   */
  async postFixComment(message) {
    const comment = `## 🔧 FixBot\n\n${message}`;
    
    try {
      await this.githubClient.createComment(this.prNumber, comment);
    } catch (error) {
      console.error('Error posting fix comment:', error);
    }
  }

  /**
   * Post error comment
   */
  async postErrorComment(errorMessage) {
    const comment = '## ❌ FixBot Error\n\n' +
      'An error occurred while applying fixes:\n\n' +
      `\`\`\`\n${errorMessage}\n\`\`\`\n\n` +
      'Please check the action logs for more details.';
    
    try {
      await this.githubClient.createComment(this.prNumber, comment);
    } catch (error) {
      console.error('Error posting error comment:', error);
    }
  }
}

module.exports = FixBot;