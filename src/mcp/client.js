/**
 * MCP (Message Code Protocol) Client for Claude Integration
 * Implements Claude's MCP protocol for intelligent code analysis
 */

const { Anthropic } = require('@anthropic-ai/sdk');
const config = require('../config/config');

class MCPClient {
  constructor() {
    if (!config.claude.apiKey) {
      throw new Error('CLAUDE_API_KEY environment variable is required');
    }
    
    this.anthropic = new Anthropic({
      apiKey: config.claude.apiKey,
    });
    
    this.protocolVersion = config.mcp.protocol;
    this.capabilities = config.mcp.capabilities;
  }

  /**
   * Initialize MCP session with Claude
   */
  async initialize() {
    console.log(`Initializing MCP client with protocol version ${this.protocolVersion}`);
    
    const initMessage = {
      jsonrpc: '2.0',
      method: 'initialize',
      params: {
        protocolVersion: this.protocolVersion,
        capabilities: this.capabilities,
        clientInfo: {
          name: 'let-them-review',
          version: '1.0.0'
        }
      }
    };
    
    return initMessage;
  }

  /**
   * Analyze code using Claude with MCP protocol
   */
  async analyzeCode(code, context = {}) {
    try {
      const prompt = this.buildAnalysisPrompt(code, context);
      
      const response = await this.anthropic.messages.create({
        model: config.claude.model,
        max_tokens: config.claude.maxTokens,
        messages: [
          {
            role: 'user',
            content: prompt
          }
        ]
      });

      return this.parseResponse(response);
    } catch (error) {
      console.error('Error analyzing code with Claude:', error);
      throw error;
    }
  }

  /**
   * Generate code fixes using Claude
   */
  async generateFixes(issues, originalCode, context = {}) {
    try {
      const prompt = this.buildFixPrompt(issues, originalCode, context);
      
      const response = await this.anthropic.messages.create({
        model: config.claude.model,
        max_tokens: config.claude.maxTokens,
        messages: [
          {
            role: 'user',
            content: prompt
          }
        ]
      });

      return this.parseFixes(response);
    } catch (error) {
      console.error('Error generating fixes with Claude:', error);
      throw error;
    }
  }

  /**
   * Build analysis prompt for code review
   */
  buildAnalysisPrompt(code, context) {
    const { filename, language, pullRequestContext } = context;
    
    return `You are an expert code reviewer using the MCP protocol. Analyze the following code and provide detailed feedback.

File: ${filename || 'unknown'}
Language: ${language || 'unknown'}
Pull Request Context: ${pullRequestContext || 'No additional context'}

Code to analyze:
\`\`\`${language || ''}
${code}
\`\`\`

Please provide a comprehensive analysis including:
1. **Summary**: Brief overview of what this code does
2. **Issues Found**: Any bugs, security vulnerabilities, or performance problems
3. **Code Quality**: Assessment of readability, maintainability, and adherence to best practices
4. **Suggestions**: Specific recommendations for improvement
5. **Security**: Any security concerns or recommendations
6. **Performance**: Performance implications and optimization opportunities

Format your response as structured JSON with the following schema:
{
  "summary": "Brief description",
  "issues": [
    {
      "type": "bug|security|performance|style",
      "severity": "high|medium|low",
      "line": number or null,
      "description": "Issue description",
      "suggestion": "How to fix it"
    }
  ],
  "overallRating": "excellent|good|fair|needs-improvement",
  "recommendations": ["recommendation1", "recommendation2"]
}`;
  }

  /**
   * Build fix prompt for automated corrections
   */
  buildFixPrompt(issues, originalCode, context) {
    const { filename, language } = context;
    
    return `You are an expert code fixer using the MCP protocol. Generate specific code fixes for the identified issues.

File: ${filename || 'unknown'}
Language: ${language || 'unknown'}

Original Code:
\`\`\`${language || ''}
${originalCode}
\`\`\`

Issues to Fix:
${issues.map((issue, index) => `
${index + 1}. ${issue.type.toUpperCase()} (${issue.severity}): ${issue.description}
   Suggestion: ${issue.suggestion}
   Line: ${issue.line || 'N/A'}
`).join('')}

Please provide the corrected code that addresses these issues. Return ONLY the fixed code without any explanation or markdown formatting. Ensure that:
1. All identified issues are addressed
2. The code maintains its original functionality
3. No new issues are introduced
4. The code follows best practices for the language`;
  }

  /**
   * Parse Claude's response for code analysis
   */
  parseResponse(response) {
    try {
      const content = response.content[0].text;
      
      // Try to extract JSON from the response
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0]);
      }
      
      // Fallback to parsing the text response
      return this.parseTextResponse(content);
    } catch (error) {
      console.error('Error parsing Claude response:', error);
      return {
        summary: 'Error parsing response',
        issues: [],
        overallRating: 'unknown',
        recommendations: []
      };
    }
  }

  /**
   * Parse Claude's response for code fixes
   */
  parseFixes(response) {
    try {
      const content = response.content[0].text;
      
      // Extract code from markdown blocks if present
      const codeMatch = content.match(/```(?:\w+)?\n([\s\S]*?)\n```/);
      if (codeMatch) {
        return codeMatch[1];
      }
      
      // Return the content as-is if no code block found
      return content;
    } catch (error) {
      console.error('Error parsing fixes:', error);
      return null;
    }
  }

  /**
   * Fallback text response parser
   */
  parseTextResponse(content) {
    return {
      summary: content.substring(0, 200) + '...',
      issues: [],
      overallRating: 'unknown',
      recommendations: ['Manual review recommended']
    };
  }

  /**
   * Health check for MCP connection
   */
  async healthCheck() {
    try {
      const response = await this.anthropic.messages.create({
        model: config.claude.model,
        max_tokens: 100,
        messages: [
          {
            role: 'user',
            content: 'Respond with "MCP connection healthy" if you can process this message.'
          }
        ]
      });
      
      return response.content[0].text.includes('healthy');
    } catch (error) {
      console.error('MCP health check failed:', error);
      return false;
    }
  }
}

module.exports = MCPClient;