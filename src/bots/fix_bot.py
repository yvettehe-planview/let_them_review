import os
import requests
import re
import json
from github import Github, Auth
from dotenv import load_dotenv

class FixBot:
    def __init__(self):
        load_dotenv()
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        auth = Auth.Token(github_token)
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
            
            # Process only the ReviewBot comments from this runtime
            for review_comment in review_comments:
                # Handle both old format (string) and new format (dict with comment_id)
                if isinstance(review_comment, dict):
                    comment_text = review_comment.get("text", "")
                    comment_id = review_comment.get("comment_id")
                elif isinstance(review_comment, str):
                    comment_text = review_comment
                    comment_id = None
                else:
                    continue
                    
                if "🤖" in comment_text and "SUGGEST_FIX" in comment_text:
                    # Create fixes and reply to the specific comment
                    fix_result = await self._create_suggested_fix(repo, pr, comment_text, 
                                                                custom_instruction, comment_id, "issue_comment")
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
            suggestions_created = self._create_suggestions(pr, fixes, filename, file_patch, comment_id, comment_type)
            
            if suggestions_created > 0:
                summary_text = f"🤖 **FixBot Analysis for {filename}**\n\n✅ Created {suggestions_created} suggestions"
                self._post_comment(repo.full_name, pr.number, summary_text, comment_id, comment_type)
            
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
    
    def _create_suggestions(self, pr, fixes: list, filename: str, file_patch: str, comment_id: int = None, comment_type: str = "issue_comment") -> int:
        """Create GitHub suggestions - reply to ReviewBot's comment with fixes"""
        if not fixes:
            return 0
            
        # Create a single reply with all suggestions
        suggestions_text = f"🔧 **FixBot Suggestions for {filename}:**\n\n"
        
        for i, fix in enumerate(fixes):
            confidence_emoji = "🟢" if fix['confidence'] >= 0.9 else "🟡" if fix['confidence'] >= 0.7 else "🔴"
            guidance = self._get_guidance(fix['confidence'])
            
            suggestions_text += (
                f"**Suggestion #{i+1}** {confidence_emoji}\n"
                f"```{filename.split('.')[-1]}\n{fix['code']}\n```\n"
                f"**Confidence:** {fix['confidence']:.0%} | **Issue:** {fix['issue']}\n"
                f"{guidance}\n\n"
            )
        
        # Reply to ReviewBot's comment
        if comment_id:
            self._post_comment(pr.base.repo.full_name, pr.number, suggestions_text, comment_id, "issue_comment")
            return len(fixes)
        else:
            # Fallback to new comment
            try:
                pr.create_issue_comment(suggestions_text)
                return len(fixes)
            except Exception:
                return 0
    
    def _get_guidance(self, confidence: float) -> str:
        """Get acceptance guidance based on confidence"""
        if confidence >= 0.9:
            return "✅ **Recommended** - High confidence, safe to apply"
        elif confidence >= 0.7:
            return "⚠️ **Review suggested** - Good confidence, please verify"
        elif confidence >= 0.5:
            return "🔍 **Manual review required** - Moderate confidence, check carefully"
        else:
            return "❌ **Use with caution** - Low confidence, likely needs modification"
    
    def _post_comment(self, repo_name: str, pr_number: int, text: str, comment_id: int = None, comment_type: str = "issue_comment"):
        """Post comment as reply or new comment"""
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            
            if comment_id:
                # Create issue comment as reply (GitHub will show them in sequence)
                pr.create_review_comment_reply(comment_id, text)
                print(f"Posted reply to comment {comment_id}")
            else:
                pr.create_issue_comment(text)
        except Exception as e:
            print(f"Error posting comment: {str(e)}, comment_id: {comment_id}, text: {text}")
    
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
        prompt = (
            "Create specific code fixes for this review feedback:\n\n"
            f"Review: {review_comment}\n"
            f"Current code diff: {file_patch}\n\n"
            "Generate ONLY valid JSON with actual code improvements:\n"
            '[{"issue": "Add loading state", "code": "const [isDeleting, setIsDeleting] = useState(false);", "confidence": 0.9}]\n\n'
            "For this review, create fixes that:\n"
            "- Add loading state if mentioned\n"
            "- Use Promise.all for batch operations if mentioned\n"
            "- Add proper error handling\n"
            "- Provide complete, working code snippets\n"
            "- Use confidence 0.8-0.95 for good fixes"
        )
        
        if custom_instruction:
            prompt += f"\n\nAdditional instruction: {custom_instruction}"
            
        try:
            response = self._call_falcon_ai(prompt)
            
            # Extract JSON from markdown code blocks if present
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON array directly
                json_match = re.search(r'\[\s*{[\s\S]*}\s*\]', response)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response
            
            fixes = json.loads(json_str)
            
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
        except Exception as e:
            print(f"Failed to parse AI response: {str(e)}")
            print(f"Full AI response: {response}")
            return []
    
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
        
        prompt = (
            "Answer this question about a GitHub PR from a code fixing perspective:\n\n"
            f"Question: {question}\n\n"
            "PR Context:\n"
            f"- Title: {pr.title}\n"
            f"- Description: {pr.body or 'No description'}\n"
            f"- Files changed: {files_summary}\n\n"
            "Provide a direct, helpful answer focused on code improvements and fixes in 2-3 sentences."
        )
        
        return self._call_falcon_ai(prompt)