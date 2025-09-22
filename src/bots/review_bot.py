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
    
    async def review_pr(self, repo_name: str, pr_number: int):
        """Review a specific PR"""
        try:
            # Get PR details
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            
            # Get PR changes
            changes = list(pr.get_files())
            review_comments = []
            
            # Generate AI summary
            python_files = [f for f in changes if f.filename.endswith('.py')]
            
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
            
            # AI review each Python file
            for file in python_files:
                if file.patch:
                    # Call AI API for code review
                    ai_review = self._get_ai_review(file.filename, file.patch)
                    
                    # Post AI review as PR comment
                    pr.create_issue_comment(f"🤖 **AI Review for {file.filename}:**\n{ai_review}")
                    review_comments.append(f"🤖 {file.filename}:\n{ai_review}")
            
            return review_comments
                    
        except Exception as e:
            return [f"Error reviewing PR: {str(e)}"]
    
    def _get_ai_review(self, filename: str, patch: str) -> str:
        """Get AI review for a code patch"""
        prompt = f"""Review this Python code change and provide specific suggestions:

File: {filename}
Code changes:
{patch}

Provide a detailed code review with:
1. Code quality issues
2. Security concerns  
3. Performance improvements
4. Best practices suggestions
5. Bug detection

Be specific and actionable."""
        return self._call_falcon_ai(prompt)
    
    def _get_ai_summary(self, title: str, description: str, changes: str) -> str:
        """Get AI summary of the entire PR"""
        prompt = f"""Analyze this Pull Request and provide a comprehensive summary:

PR Title: {title}
Description: {description}

Code Changes:
{changes[:3000]}

Provide:
1. What this PR does (main purpose)
2. Key changes made
3. Potential impact
4. Overall code quality assessment
5. Recommendations

Be concise but thorough."""
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