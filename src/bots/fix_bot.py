import os
import requests
import re
from github import Github, Auth
from dotenv import load_dotenv

class FixBot:
    def __init__(self):
        load_dotenv()
        auth = Auth.Token(os.getenv('GITHUB_TOKEN'))
        self.github = Github(auth=auth)
        self.falcon_api_key = os.getenv('FALCON_API_KEY')
        self.base_url = "https://falconai.planview-prod.io"
    
    async def fix_code(self, repo_name: str, pr_number: int, review_comments: list, custom_instruction: str = None):
        """Generate AI-powered fixes as GitHub suggested changes"""
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            fixes_applied = []
            
            for comment in review_comments:
                if isinstance(comment, str):
                    # Process both ReviewBot comments and direct FixBot mentions
                    if "🤖" in comment:
                        # Skip AI Summary - only process file-specific reviews
                        if "AI Summary:" in comment:
                            continue
                        fix_result = await self._create_suggested_fix(repo, pr, comment, custom_instruction)
                    else:
                        # Handle direct FixBot mentions - analyze the entire PR
                        fix_result = await self._analyze_pr_for_fixes(repo, pr, comment, custom_instruction)
                    
                    if fix_result and "Created" in fix_result:
                        fixes_applied.append(fix_result)
            
            if not fixes_applied:
                # Post positive feedback when no fixes are needed
                pr.create_issue_comment("🤖 **FixBot** ✅\n\nCode looks good! No issues found that require fixes. Great work!\n\n*Powered by AI Code Review System*")
                return ["No fixes needed - posted positive feedback"]
            
            return fixes_applied
        except Exception as e:
            return [f"Error creating fixes: {str(e)}"]
    
    async def _create_suggested_fix(self, repo, pr, review_comment, custom_instruction: str = None):
        """Create GitHub suggested change for the fix"""
        try:
            # Try multiple patterns to extract filename (any file type)
            patterns = [
                r'🤖 ([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+):',  # "🤖 file.ext:"
                r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+):',     # "file.ext:"
                r'`([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)`',    # "`file.ext`"
                r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)',      # Any file with extension
            ]
            
            filename = None
            for pattern in patterns:
                matches = re.findall(pattern, review_comment)
                if matches:
                    filename = matches[0]

                    break
            
            if not filename:
                return "Could not identify file to fix"
            
            # Get file patch
            file_patch = None
            for f in pr.get_files():
                if f.filename == filename:
                    file_patch = f.patch
                    break
            
            if not file_patch:
                return f"Could not find changes for {filename}"
            
            # Generate multiple targeted fixes with confidence scores
            fixes = await self._generate_partial_fixes(review_comment, file_patch, custom_instruction)
            
            # Show all fixes with confidence scores, create suggestions for high-confidence ones
            suggestions_created = 0
            low_confidence_fixes = []
            
            for i, fix in enumerate(fixes):
                confidence_emoji = "🟢" if fix['confidence'] >= 0.9 else "🟡" if fix['confidence'] >= 0.7 else "🔴"
                
                if fix['confidence'] >= 0.7:  # Create suggestions for high-confidence fixes
                    # Add acceptance guidance based on confidence
                    if fix['confidence'] >= 0.9:
                        guidance = "✅ **Recommended** - High confidence, safe to apply"
                    elif fix['confidence'] >= 0.8:
                        guidance = "⚠️ **Review suggested** - Good confidence, please verify"
                    else:
                        guidance = "🔍 **Manual review required** - Moderate confidence, check carefully"
                    
                    pr.create_review_comment(
                        body=f"""🔧 **FixBot Suggestion #{i+1}** {confidence_emoji}

```suggestion
{fix['code']}
```

**Confidence:** {fix['confidence']:.0%} | **Issue:** {fix['issue']}

{guidance}

*Click "Apply suggestion" to commit this fix.*""",
                        commit=pr.head.sha,
                        path=filename,
                        line=fix.get('line', self._get_line_from_patch(file_patch))
                    )
                    suggestions_created += 1
                else:
                    # Track low-confidence fixes to show in summary
                    low_confidence_fixes.append(f"• {fix['issue']} (Confidence: {fix['confidence']:.0%})")
            
            # Post summary comment showing all confidence scores
            if suggestions_created > 0 or low_confidence_fixes:
                summary_parts = []
                if suggestions_created > 0:
                    summary_parts.append(f"✅ Created {suggestions_created} high-confidence suggestions")
                if low_confidence_fixes:
                    summary_parts.append(f"⚠️ Low-confidence issues detected:\n" + "\n".join(low_confidence_fixes))
                
                pr.create_issue_comment(f"🤖 **FixBot Analysis for {filename}**\n\n" + "\n\n".join(summary_parts))
            
            return f"Analyzed {filename}: {suggestions_created} suggestions created, {len(low_confidence_fixes)} low-confidence issues"
            

        except Exception as e:
            return f"Error: {str(e)}"
    
    def _call_falcon_ai(self, prompt: str) -> str:
        """Make API call to Falcon AI"""
        try:
            response = requests.post(
                f"{self.base_url}/api/chat/completions",
                headers={
                    'Authorization': f'Bearer {self.falcon_api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=90
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and result["choices"]:
                    return result["choices"][0]["message"]["content"].strip()
            
            return f"API error {response.status_code}"
        except Exception as e:
            return f"Falcon AI failed: {str(e)}"
    
    async def _ai_should_fix(self, review_comment: str) -> bool:
        """Use AI to determine if this review comment requires a code fix"""
        try:
            decision = self._call_falcon_ai(f"""Analyze this code review comment and decide if it requires a code fix:

Review Comment: {review_comment}

Respond with only "YES" if the comment identifies specific issues that need code changes, or "NO" if it's just informational, positive feedback, or general suggestions that don't require immediate code fixes.""")
            
            return "YES" in decision.upper()
        except Exception:
            # Fallback to conservative approach - assume fix is needed
            return True
    
    async def _generate_partial_fixes(self, review_comment: str, file_patch: str, custom_instruction: str = None) -> list:
        """Generate multiple targeted fixes with confidence scores"""
        base_prompt = f"""Analyze this code review and create targeted fixes:

Review: {review_comment}
Diff: {file_patch}

Provide response as JSON array with format:
[
  {{
    "issue": "Brief description of issue",
    "code": "Fixed code lines",
    "confidence": 0.95,
    "line": 10
  }}
]

Create separate fixes for different issues. Confidence: 0.0-1.0 scale."""
        
        if custom_instruction:
            prompt = f"{base_prompt}\n\nAdditional instruction: {custom_instruction}"
        else:
            prompt = base_prompt
            
        try:
            response = self._call_falcon_ai(prompt)
            
            # Try to parse JSON response
            import json
            fixes = json.loads(response)
            
            # Validate and clean fixes
            valid_fixes = []
            for fix in fixes:
                if isinstance(fix, dict) and 'code' in fix and 'confidence' in fix:
                    valid_fixes.append({
                        'issue': fix.get('issue', 'Code improvement'),
                        'code': fix['code'].strip(),
                        'confidence': min(max(fix['confidence'], 0.0), 1.0),
                        'line': fix.get('line')
                    })
            
            return valid_fixes[:3]  # Limit to 3 suggestions max
            
        except Exception:
            # Fallback to single fix
            return [{
                'issue': 'Code improvement',
                'code': '# TODO: Address code review feedback',
                'confidence': 0.5
            }]
    
    async def _analyze_pr_for_fixes(self, repo, pr, instruction: str, custom_instruction: str = None):
        """Analyze entire PR for fixes when directly mentioned"""
        try:
            # Get all changed files
            files = list(pr.get_files())
            fixes_created = 0
            
            for file in files:
                if file.patch and any(file.filename.endswith(ext) for ext in ['.py', '.js', '.ts', '.java', '.cpp', '.go']):
                    # Create a synthetic review comment for this file
                    synthetic_review = f"🤖 {file.filename}: {instruction}"
                    
                    fix_result = await self._create_suggested_fix(repo, pr, synthetic_review, custom_instruction)
                    if fix_result and "suggestions created" in fix_result:
                        fixes_created += 1
            
            return f"Analyzed PR: processed {fixes_created} files" if fixes_created > 0 else "No fixable issues found in PR"
            
        except Exception as e:
            return f"Error analyzing PR: {str(e)}"
    
    def _get_line_from_patch(self, patch: str) -> int:
        """Extract line number from patch"""
        match = re.search(r'@@\s*-\d+,?\d*\s*\+?(\d+)', patch)
        return int(match.group(1)) if match else 1