import os
import requests
from github import Github, Auth
from dotenv import load_dotenv

class ReviewBot:
    def __init__(self):
        load_dotenv()
        auth = Auth.Token(os.getenv('GITHUB_TOKEN'))
        self.github = Github(auth=auth)
        self.falcon_api_key = os.getenv('FALCON_API_KEY')
        self.base_url = "https://falconai.planview-prod.io"
        self.model_name = None
    
    def _get_best_model(self):
        self.model_name = "anthropic.claude-3-5-sonnet-20241022-v2:0" 
        return self.model_name
    
    async def review_pr(self, repo_name: str, pr_number: int, custom_instruction: str = None):
        """Review a specific PR with optional custom instruction"""
        try:
            # Get PR details
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            
            # Get PR changes
            changes = list(pr.get_files())
            review_comments = []
            
            # Filter files that should be reviewed (code files)
            reviewable_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.cs', '.jsx', '.tsx', '.vue', '.html', '.css', '.scss', '.sql', '.sh', '.yml', '.yaml', '.json', '.xml']
            reviewable_files = [f for f in changes if any(f.filename.endswith(ext) for ext in reviewable_extensions)]
            
            # Collect all changes for AI analysis
            all_changes = ""
            for file in changes:
                if file.patch:
                    all_changes += f"\n--- {file.filename} ---\n{file.patch}\n"
            
            # Get AI summary
            ai_summary = self._get_ai_summary(pr.title, pr.body or "No description", all_changes)
            
            # Post AI summary as PR comment
            pr.create_issue_comment(f"🤖 **AI Summary:**\n{ai_summary}")
            review_comments.append(f"🤖 AI Summary:\n{ai_summary}")
            
            # AI review each reviewable file
            for file in reviewable_files:
                if file.patch:
                    # Call AI API for code review
                    ai_review = self._get_ai_review(file.filename, file.patch, custom_instruction)
                    
                    # Post AI review as PR comment
                    pr.create_issue_comment(f"🤖 **AI Review for {file.filename}:**\n{ai_review}")
                    review_comments.append(f"🤖 {file.filename}:\n{ai_review}")
            
            # If no reviewable files, post positive feedback
            if not reviewable_files:
                pr.create_issue_comment("✅ **ReviewBot - No code files to review!**\n\nThis PR doesn't contain code changes that need review.")
                review_comments.append("No reviewable files found for review")
            
            return review_comments
                    
        except Exception as e:
            return [f"Error reviewing PR: {str(e)}"]
    
    def _get_ai_review(self, filename: str, patch: str, custom_instruction: str = None) -> str:
        """Get AI review for a code patch"""
        base_prompt = f"""Review ONLY the changed lines in this code diff:

File: {filename}
Code changes (diff):
{patch}

Provide a brief review focusing on:
1. Issues in the changed lines only
2. Quick suggestions for improvement

Keep response under 3 sentences. Be concise."""
        
        if custom_instruction:
            prompt = f"{base_prompt}\n\nAdditional instruction: {custom_instruction}"
        else:
            prompt = base_prompt
            
        return self._call_falcon_ai(prompt)
    
    def _get_ai_summary(self, title: str, description: str, changes: str) -> str:
        """Get AI summary of the entire PR"""
        prompt = f"""Summarize this PR in 2-3 sentences:

PR Title: {title}
Description: {description}

Code Changes:
{changes[:1000]}

What does this PR do and any major concerns?"""
        return self._call_falcon_ai(prompt)
    
    def _call_falcon_ai(self, prompt: str) -> str:
        """Make API call to Falcon AI using the best available model"""
        try:
            url = f"{self.base_url}/api/chat/completions"
            headers = {
                'Authorization': f'Bearer {self.falcon_api_key}',
                'Content-Type': 'application/json'
            }
            model = self._get_best_model()
            print(model)
            data = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Try with longer timeout for AI processing
            response = requests.post(url, headers=headers, json=data, timeout=90)
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    return f"Unexpected response format: {str(result)[:300]}"
            else:
                print(f"Chat API error: {response.status_code} - {response.text}")
                return f"API error {response.status_code}: {response.text[:200]}"
                
        except Exception as e:
            return f"Falcon AI call failed: {str(e)}"