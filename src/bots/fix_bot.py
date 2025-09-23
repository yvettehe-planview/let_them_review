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
    
    async def fix_code(self, repo_name: str, pr_number: int, review_comments: list):
        """Generate AI-powered fixes as GitHub suggested changes"""
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            fixes_applied = []
            
            for comment in review_comments:
                print(f"🔍 Checking comment: {comment[:100]}...")
                if isinstance(comment, str) and "🤖" in comment:
                    # Look for any review content, not just specific keywords
                    if any(word in comment.lower() for word in ["issues", "error", "bug", "security", "concerns", "suggestions", "review"]):
                        print(f"✅ Found fixable comment")
                        fix_result = await self._create_suggested_fix(repo, pr, comment)
                        if fix_result:
                            fixes_applied.append(fix_result)
                    else:
                        print(f"❌ No fixable keywords found")
            
            return fixes_applied or ["No fixes generated"]
        except Exception as e:
            return [f"Error creating fixes: {str(e)}"]
    
    async def _create_suggested_fix(self, repo, pr, review_comment):
        """Create GitHub suggested change for the fix"""
        try:
            filename = re.findall(r'([a-zA-Z0-9_/.-]+\.py)', review_comment)
            if not filename:
                return "Could not identify file to fix"
            filename = filename[0]
            
            # Get file patch
            file_patch = None
            for f in pr.get_files():
                if f.filename == filename:
                    file_patch = f.patch
                    break
            
            if not file_patch:
                return f"Could not find changes for {filename}"
            
            # Generate fix with AI
            fixed_code = self._call_falcon_ai(f"""Fix the changed lines in this diff:

Review: {review_comment}
Diff: {file_patch}

Provide only the fixed code lines.""")
            
            if "API error" in fixed_code or "failed" in fixed_code:
                fixed_code = "# TODO: Address code review feedback"
            
            # Create suggested change
            pr.create_review_comment(
                body=f"""🔧 **FixBot Suggestion**

```suggestion
{fixed_code}
```

*Click "Apply suggestion" to commit this fix.*""",
                commit=pr.head.sha,
                path=filename,
                line=self._get_line_from_patch(file_patch)
            )
            
            return f"Created suggested change for {filename}"
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
    
    def _get_line_from_patch(self, patch: str) -> int:
        """Extract line number from patch"""
        match = re.search(r'@@\s*-\d+,?\d*\s*\+?(\d+)', patch)
        return int(match.group(1)) if match else 1