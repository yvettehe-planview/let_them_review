/**
 * ReviewBot - AI-powered code review agent
 * Analyzes pull requests and provides intelligent feedback using Claude MCP
 */

const MCPClient = require('../mcp/client');
const GitHubClient = require('../utils/github');
const config = require('../config/config');

class ReviewBot {
  constructor() {
    this.mcpClient = new MCPClient();
    this.githubClient = new GitHubClient();
    this.prNumber = process.env.PR_NUMBER;
    
    if (!this.prNumber) {
      throw new Error('PR_NUMBER environment variable is required');
    }
  }

  /**
   * Main entry point for reviewing a pull request
   */
  async reviewPullRequest() {
    try {
      console.log(`🤖 ReviewBot starting analysis for PR #${this.prNumber}`);
      
      // Initialize MCP connection
      await this.mcpClient.initialize();
      
      // Health check
      const isHealthy = await this.mcpClient.healthCheck();
      if (!isHealthy) {
        throw new Error('MCP connection health check failed');
      }
      
      // Get PR details
      const pullRequest = await this.githubClient.getPullRequest(this.prNumber);
      console.log(`Analyzing PR: ${pullRequest.title}`);
      
      // Get changed files
      const files = await this.githubClient.getPullRequestFiles(this.prNumber);
      const filteredFiles = this.githubClient.filterFiles(files);
      
      console.log(`Found ${filteredFiles.length} files to review (${files.length} total)`);
      
      if (filteredFiles.length === 0) {
        await this.postSummaryComment('No reviewable files found in this PR.');
        return;
      }
      
      // Limit files for review
      const filesToReview = filteredFiles.slice(0, config.reviewBot.maxFilesPerReview);
      
      // Analyze each file
      const reviews = [];
      for (const file of filesToReview) {
        console.log(`Analyzing ${file.filename}...`);
        const review = await this.analyzeFile(file, pullRequest);
        if (review) {
          reviews.push(review);
        }
      }
      
      // Generate summary and post comments
      await this.generateSummary(reviews, pullRequest);
      await this.postFileComments(reviews);
      
      console.log('✅ ReviewBot analysis complete');
      
    } catch (error) {
      console.error('❌ ReviewBot error:', error);
      await this.postErrorComment(error.message);
    }
  }

  /**
   * Analyze a single file
   */
  async analyzeFile(file, pullRequest) {
    try {
      // Skip files that are too large or binary
      if (file.additions + file.deletions > 1000) {
        console.log(`Skipping ${file.filename} - too large (${file.additions + file.deletions} changes)`);
        return null;
      }

      // Detect language
      const language = this.githubClient.detectLanguage(file.filename);
      
      // Get file content based on status
      let content = '';
      if (file.status === 'added' || file.status === 'modified') {
        // Get the patch content
        content = file.patch || '';
      } else if (file.status === 'removed') {
        // For removed files, we don't need to analyze
        return null;
      }

      if (!content.trim()) {
        return null;
      }

      // Prepare context for analysis
      const context = {
        filename: file.filename,
        language: language,
        pullRequestContext: `PR #${pullRequest.number}: ${pullRequest.title}\n${pullRequest.body || ''}`,
        fileStatus: file.status,
        additions: file.additions,
        deletions: file.deletions
      };

      // Analyze with Claude MCP
      const analysis = await this.mcpClient.analyzeCode(content, context);
      
      return {
        file: file,
        analysis: analysis,
        context: context
      };
      
    } catch (error) {
      console.error(`Error analyzing ${file.filename}:`, error);
      return null;
    }
  }

  /**
   * Generate overall PR summary
   */
  async generateSummary(reviews, pullRequest) {
    try {
      const totalIssues = reviews.reduce((sum, review) => sum + review.analysis.issues.length, 0);
      const highSeverityIssues = reviews.reduce((sum, review) => 
        sum + review.analysis.issues.filter(issue => issue.severity === 'high').length, 0);
      
      // Determine overall assessment
      let overallAssessment = '✅ **APPROVED** - Code looks good!';
      let emoji = '✅';
      
      if (highSeverityIssues > 0) {
        overallAssessment = '❌ **CHANGES REQUESTED** - High severity issues found';
        emoji = '❌';
      } else if (totalIssues > 5) {
        overallAssessment = '⚠️ **NEEDS IMPROVEMENT** - Multiple issues found';
        emoji = '⚠️';
      } else if (totalIssues > 0) {
        overallAssessment = '📝 **APPROVED WITH SUGGESTIONS** - Minor issues found';
        emoji = '📝';
      }

      // Build summary
      const summary = this.buildSummaryComment(reviews, pullRequest, overallAssessment, emoji, totalIssues, highSeverityIssues);
      
      // Post as PR review
      const event = highSeverityIssues > 0 ? 'REQUEST_CHANGES' : 'COMMENT';
      await this.githubClient.createReview(this.prNumber, summary, event);
      
    } catch (error) {
      console.error('Error generating summary:', error);
    }
  }

  /**
   * Build summary comment text
   */
  buildSummaryComment(reviews, pullRequest, overallAssessment, emoji, totalIssues, highSeverityIssues) {
    let summary = `## ${emoji} ReviewBot Analysis\n\n`;
    summary += `${overallAssessment}\n\n`;
    
    summary += '### 📊 Summary\n';
    summary += `- **Files analyzed:** ${reviews.length}\n`;
    summary += `- **Total issues:** ${totalIssues}\n`;
    summary += `- **High severity:** ${highSeverityIssues}\n\n`;
    
    if (reviews.length > 0) {
      summary += '### 📁 Files Reviewed\n';
      for (const review of reviews) {
        const rating = this.getRatingEmoji(review.analysis.overallRating);
        const issueCount = review.analysis.issues.length;
        summary += `- ${rating} \`${review.file.filename}\` (${issueCount} issues)\n`;
      }
      summary += '\n';
    }
    
    // Aggregate recommendations
    const allRecommendations = reviews.flatMap(r => r.analysis.recommendations || []);
    const uniqueRecommendations = [...new Set(allRecommendations)];
    
    if (uniqueRecommendations.length > 0) {
      summary += '### 💡 Key Recommendations\n';
      uniqueRecommendations.slice(0, 5).forEach(rec => {
        summary += `- ${rec}\n`;
      });
      summary += '\n';
    }
    
    // Issue breakdown
    if (totalIssues > 0) {
      const issuesByType = {};
      reviews.forEach(review => {
        review.analysis.issues.forEach(issue => {
          issuesByType[issue.type] = (issuesByType[issue.type] || 0) + 1;
        });
      });
      
      summary += '### 🔍 Issue Breakdown\n';
      Object.entries(issuesByType).forEach(([type, count]) => {
        const typeEmoji = this.getTypeEmoji(type);
        summary += `- ${typeEmoji} ${type}: ${count}\n`;
      });
      summary += '\n';
    }
    
    summary += '---\n';
    summary += '🤖 *This review was generated by ReviewBot using Claude MCP. For fixes, comment `@fixbot` on specific issues.*';
    
    return summary;
  }

  /**
   * Post individual file comments
   */
  async postFileComments(reviews) {
    for (const review of reviews) {
      if (review.analysis.issues.length === 0) continue;
      
      for (const issue of review.analysis.issues) {
        try {
          const comment = this.buildIssueComment(issue, review.file.filename);
          
          // For now, post as general PR comment since we need proper line mapping for review comments
          await this.githubClient.createComment(this.prNumber, comment);
          
        } catch (error) {
          console.error(`Error posting comment for ${review.file.filename}:`, error);
        }
      }
    }
  }

  /**
   * Build issue comment text
   */
  buildIssueComment(issue, filename) {
    const typeEmoji = this.getTypeEmoji(issue.type);
    const severityEmoji = this.getSeverityEmoji(issue.severity);
    
    let comment = `## ${typeEmoji} ${issue.type.toUpperCase()} ${severityEmoji}\n\n`;
    comment += `**File:** \`${filename}\`\n`;
    if (issue.line) {
      comment += `**Line:** ${issue.line}\n`;
    }
    comment += `**Severity:** ${issue.severity}\n\n`;
    comment += `**Issue:** ${issue.description}\n\n`;
    comment += `**Suggestion:** ${issue.suggestion}\n\n`;
    comment += '---\n';
    comment += '🤖 *To apply an automated fix, reply with `@fixbot apply`*';
    
    return comment;
  }

  /**
   * Post error comment
   */
  async postErrorComment(errorMessage) {
    const comment = '## ❌ ReviewBot Error\n\n' +
      'An error occurred during the analysis:\n\n' +
      `\`\`\`\n${errorMessage}\n\`\`\`\n\n` +
      'Please check the action logs for more details.';
    
    try {
      await this.githubClient.createComment(this.prNumber, comment);
    } catch (error) {
      console.error('Error posting error comment:', error);
    }
  }

  /**
   * Post summary comment
   */
  async postSummaryComment(message) {
    const comment = `## 🤖 ReviewBot\n\n${message}`;
    
    try {
      await this.githubClient.createComment(this.prNumber, comment);
    } catch (error) {
      console.error('Error posting summary comment:', error);
    }
  }

  /**
   * Get emoji for rating
   */
  getRatingEmoji(rating) {
    const emojiMap = {
      'excellent': '🟢',
      'good': '🔵',
      'fair': '🟡',
      'needs-improvement': '🔴',
      'unknown': '⚪'
    };
    return emojiMap[rating] || '⚪';
  }

  /**
   * Get emoji for issue type
   */
  getTypeEmoji(type) {
    const emojiMap = {
      'bug': '🐛',
      'security': '🔒',
      'performance': '⚡',
      'style': '🎨',
      'refactor': '♻️',
      'architecture': '🏗️',
      'documentation': '📚'
    };
    return emojiMap[type] || '⚠️';
  }

  /**
   * Get emoji for severity
   */
  getSeverityEmoji(severity) {
    const emojiMap = {
      'high': '🔴',
      'medium': '🟡',
      'low': '🟢'
    };
    return emojiMap[severity] || '⚪';
  }
}

module.exports = ReviewBot;