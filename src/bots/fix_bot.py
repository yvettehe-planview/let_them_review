import os
import requests
import re
import json
from github import Github, Auth
from dotenv import load_dotenv

class FixBot:
    def __init__(self):
        load_dotenv()
        auth = Auth.Token(os.getenv('GITHUB_TOKEN'))
        self.github = Github(auth=auth)
        self.falcon_api_key = os.getenv('FALCON_API_KEY')
        self.base_url = "https://falconai.planview-prod.io"
    
    async def fix_code(self, repo_name: str, pr_number: int, review_comments: list, custom_instruction: str = None, comment_id: int = None, comment_type: str = "issue_comment"):
        """Generate AI-powered fixes as GitHub suggested changes"""
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            fixes_applied = []
            
            # If there's a custom instruction and comment_id, respond directly to the question
            if custom_instruction and comment_id:
                response = await self._answer_question(pr, custom_instruction)
                self._post_comment(repo_name, pr_number, f"🤖 **FixBot:**\n{response}", comment_id, comment_type)
                return [f"Direct response: {response}"]
            
            # Otherwise, process review comments for fixes
            for comment in review_comments:
                if isinstance(comment, str):
                    if "🤖" in comment and "AI Summary:" not in comment:
                        fix_result = await self._create_suggested_fix(repo, pr, comment, custom_instruction, comment_id, comment_type)
                    else:
                        fix_result = await self._analyze_pr_for_fixes(repo, pr, comment, custom_instruction, comment_id, comment_type)
                    
                    if fix_result and "Created" in fix_result:
                        fixes_applied.append(fix_result)
            
            if not fixes_applied:
                self._post_comment(repo_name, pr_number, "🤖 **FixBot** ✅\n\nCode looks good! No issues found that require fixes.", comment_id, comment_type)
                return ["No fixes needed - posted positive feedback"]
            
            return fixes_applied
        except Exception as e:
            return [f"Error creating fixes: {str(e)}"]
    
    async def _create_suggested_fix(self, repo, pr, review_comment, custom_instruction: str = None, comment_id: int = None, comment_type: str = "issue_comment"):
        """Create GitHub suggested change for the fix"""
        try:
            filename = self._extract_filename(review_comment)
            if not filename:
                return "Could not identify file to fix"
            
            file_patch = self._get_file_patch(pr, filename)
            if not file_patch:
                return f"Could not find changes for {filename}"
            
            fixes = await self._generate_partial_fixes(review_comment, file_patch, custom_instruction)
            suggestions_created = self._create_suggestions(pr, fixes, filename, file_patch)
            
            if suggestions_created > 0:
                summary_text = f"🤖 **FixBot Analysis for {filename}**\n\n✅ Created {suggestions_created} suggestions"
                self._post_comment(repo.name, pr.number, summary_text, comment_id, comment_type)
            
            return f"Created {suggestions_created} suggestions for {filename}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _extract_filename(self, review_comment: str) -> str:
        """Extract filename from review comment"""
        patterns = [
            r'🤖 ([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+):',
            r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+):',
            r'`([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)`',
            r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, review_comment)
            if matches:
                return matches[0]
        return None
    
    def _get_file_patch(self, pr, filename: str) -> str:
        """Get patch for specific file"""
        for f in pr.get_files():
            if f.filename == filename:
                return f.patch
        return None
    
    def _create_suggestions(self, pr, fixes: list, filename: str, file_patch: str) -> int:
        """Create GitHub suggestions for high-confidence fixes"""
        suggestions_created = 0
        
        for i, fix in enumerate(fixes):
            if fix['confidence'] >= 0.7:
                confidence_emoji = "🟢" if fix['confidence'] >= 0.9 else "🟡"
                guidance = self._get_guidance(fix['confidence'])
                
                pr.create_review_comment(
                    body=f"""🔧 **FixBot Suggestion #{i+1}** {confidence_emoji}

```suggestion
{fix['code']}
```

**Confidence:** {fix['confidence']:.0%} | **Issue:** {fix['issue']}

{guidance}""",
                    commit=pr.head.sha,
                    path=filename,
                    line=fix.get('line', self._get_line_from_patch(file_patch))
                )
                suggestions_created += 1
        
        return suggestions_created
    
    def _get_guidance(self, confidence: float) -> str:
        """Get acceptance guidance based on confidence"""
        if confidence >= 0.9:
            return "✅ **Recommended** - High confidence, safe to apply"
        elif confidence >= 0.8:
            return "⚠️ **Review suggested** - Good confidence, please verify"
        else:
            return "🔍 **Manual review required** - Moderate confidence, check carefully"
    
    def _post_comment(self, repo_name: str, pr_number: int, text: str, comment_id: int = None, comment_type: str = "issue_comment"):
        """Post comment as reply or new comment"""
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            
            if comment_id and comment_type == "review_comment":
                try:
                    pr.create_review_comment_reply(comment_id, text)
                except Exception as e:
                    print(f"Failed to reply to review comment: {str(e)}")
                    pr.create_issue_comment(text)
            else:
                pr.create_issue_comment(text)
        except Exception as e:
            print(f"Error posting comment: {str(e)}")
    
    def _call_falcon_ai(self, prompt: str) -> str:
        """Make API call to Falcon AI"""
        try:
            response = requests.post(
                f"{self.base_url}/api/chat/completions",
                headers={'Authorization': f'Bearer {self.falcon_api_key}', 'Content-Type': 'application/json'},
                json={"model": "anthropic.claude-3-5-sonnet-20241022-v2:0", "messages": [{"role": "user", "content": prompt}]},
                timeout=90
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and result["choices"]:
                    return result["choices"][0]["message"]["content"].strip()
            
            return f"API error {response.status_code}"
        except Exception as e:
            return f"Falcon AI failed: {str(e)}"
    
    async def _generate_partial_fixes(self, review_comment: str, file_patch: str, custom_instruction: str = None) -> list:
        """Generate multiple targeted fixes with confidence scores"""
        prompt = f"""Analyze this code review and create targeted fixes:

Review: {review_comment}
Diff: {file_patch}

Provide JSON array: [{{"issue": "Brief description", "code": "Fixed code", "confidence": 0.95, "line": 10}}]

Create separate fixes for different issues. Confidence: 0.0-1.0 scale."""
        
        if custom_instruction:
            prompt += f"\n\nAdditional instruction: {custom_instruction}"
            
        try:
            response = self._call_falcon_ai(prompt)
            fixes = json.loads(response)
            
            valid_fixes = []
            for fix in fixes:
                if isinstance(fix, dict) and 'code' in fix and 'confidence' in fix:
                    valid_fixes.append({
                        'issue': fix.get('issue', 'Code improvement'),
                        'code': fix['code'].strip(),
                        'confidence': min(max(fix['confidence'], 0.0), 1.0),
                        'line': fix.get('line')
                    })
            
            return valid_fixes[:3]
        except Exception:
            return [{'issue': 'Code improvement', 'code': '# TODO: Address code review feedback', 'confidence': 0.5}]
    
    async def _analyze_pr_for_fixes(self, repo, pr, instruction: str, custom_instruction: str = None, comment_id: int = None, comment_type: str = "issue_comment"):
        """Analyze entire PR for fixes when directly mentioned"""
        try:
            files = list(pr.get_files())
            fixes_created = 0
            
            for file in files:
                if file.patch and any(file.filename.endswith(ext) for ext in ['.py', '.js', '.ts', '.java', '.cpp', '.go']):
                    synthetic_review = f"🤖 {file.filename}: {instruction}"
                    fix_result = await self._create_suggested_fix(repo, pr, synthetic_review, custom_instruction)
                    if fix_result and "Created" in fix_result:
                        fixes_created += 1
            
            return f"Analyzed PR: processed {fixes_created} files" if fixes_created > 0 else "No fixable issues found"
        except Exception as e:
            return f"Error analyzing PR: {str(e)}"
    
    async def _answer_question(self, pr, question: str) -> str:
        """Answer a specific question about the PR"""
        files_summary = ", ".join([f.filename for f in pr.get_files()][:5])
        if len(list(pr.get_files())) > 5:
            files_summary += "..."
        
        prompt = f"""Answer this question about a GitHub PR from a code fixing perspective:

Question: {question}

PR Context:
- Title: {pr.title}
- Description: {pr.body or 'No description'}
- Files changed: {files_summary}

Provide a direct, helpful answer focused on code improvements and fixes in 2-3 sentences."""
        
        return self._call_falcon_ai(prompt)
    
    def _get_line_from_patch(self, patch: str) -> int:
        """Extract line number from patch"""
        match = re.search(r'@@\s*-\d+,?\d*\s*\+?(\d+)', patch)
        return int(match.group(1)) if match else 1