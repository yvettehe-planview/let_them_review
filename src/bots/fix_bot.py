import os
import requests
from github import Github, Auth
from dotenv import load_dotenv

class FixBot:
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
    
    async def fix_code(self, repo_name: str, pr_number: int, review_comments: list):
        """Generate AI-powered fixes based on review comments"""
        try:
            repo = self.github.get_repo(repo_name)
            original_pr = repo.get_pull(pr_number)
            fixes_applied = []
            
            for comment in review_comments:
                if "🤖" in comment and ("issues" in comment.lower() or "error" in comment.lower() or "bug" in comment.lower()):
                    # Generate AI fix suggestions
                    fix_suggestion = self._generate_fix_suggestion(comment)
                    
                    # Post fix suggestion as PR comment
                    fix_comment = f"🔧 **FixBot Response:**\n\n{fix_suggestion}"
                    original_pr.create_issue_comment(fix_comment)
                    fixes_applied.append(f"Posted AI-generated fix suggestion")
            
            return fixes_applied or ["No fixes needed"]
            
        except Exception as e:
            return [f"Error creating fixes: {str(e)}"]
    
    def _generate_fix_suggestion(self, review_comment: str) -> str:
        """Generate AI-powered fix suggestions"""
        prompt = f"""Based on this code review comment, provide specific fix suggestions:

Review Comment:
{review_comment}

Please provide:
1. Specific code changes needed
2. Step-by-step implementation guide
3. Alternative approaches if applicable
4. Best practices to follow
5. Example code snippets where helpful

Be practical and actionable."""
        return self._call_falcon_ai(prompt)
    
    def _call_falcon_ai(self, prompt: str) -> str:
        """Make API call to Falcon AI with retry mechanism"""
        url = f"{self.base_url}/api/chat/completions"
        headers = {
            'Authorization': f'Bearer {self.falcon_api_key}',
            'Content-Type': 'application/json'
        }
        model = self._get_best_model()
        data = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Try with different timeout settings
        timeouts = [60, 90, 120]  # Longer timeouts for AI processing
        
        for timeout in timeouts:
            try:
                print(f"Trying Falcon AI with {timeout}s timeout...")
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
                
                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"].strip()
                    else:
                        return f"Unexpected response format: {str(result)[:300]}"
                else:
                    print(f"API error {response.status_code}: {response.text[:100]}")
                    if timeout == timeouts[-1]:  # Last attempt
                        return f"API error {response.status_code}: {response.text[:200]}"
                    continue
                    
            except requests.exceptions.Timeout:
                print(f"Timeout after {timeout}s, trying longer timeout...")
                if timeout == timeouts[-1]:  # Last attempt
                    return "Falcon AI timeout - service may be overloaded. Please try again later."
                continue
            except Exception as e:
                if timeout == timeouts[-1]:  # Last attempt
                    return f"Falcon AI call failed: {str(e)}"
                continue
        
        return "All retry attempts failed"