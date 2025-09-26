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

    async def review_pr(self, repo_name: str, pr_number: int, custom_instruction: str = None, 
                       comment_id: int = None, comment_type: str = "issue_comment"):
        """Review a specific PR with optional custom instruction"""
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            # Direct question response mode
            if custom_instruction and comment_id:
                response = await self._answer_question(pr, custom_instruction)
                self._post_comment(repo_name, pr_number, f"🤖 **ReviewBot:**\n{response}", 
                                 comment_id, comment_type)
                return [f"Direct response: {response}"]

            # Full PR analysis mode
            changes = list(pr.get_files())
            review_comments = []

            reviewable_extensions = [
                '.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.php', '.rb', 
                '.swift', '.kt', '.scala', '.cs', '.jsx', '.tsx', '.vue', '.html', '.css', 
                '.scss', '.sql', '.sh', '.yml', '.yaml', '.json', '.xml'
            ]
            reviewable_files = [f for f in changes 
                              if any(f.filename.endswith(ext) for ext in reviewable_extensions)]

            # Collect all changes for AI summary
            all_changes = ""
            for file in changes:
                if file.patch:
                    all_changes += f"\n--- {file.filename} ---\n{file.patch}\n"

            # Generate and post AI summary
            ai_summary = self._get_ai_summary(pr.title, pr.body or "No description", all_changes)
            summary_text = f"🤖 **AI Summary:**\n{ai_summary}"
            summary_comment_id = self._post_comment(repo_name, pr_number, summary_text, comment_id, comment_type)
            review_comments.append({"text": f"🤖 AI Summary:\n{ai_summary}", "comment_id": summary_comment_id})

            # Review each reviewable file
            for file in reviewable_files:
                if file.patch:
                    ai_review = self._get_ai_review(file.filename, file.patch, custom_instruction)
                    review_text = f"🤖 **AI Review for {file.filename}:**\n{ai_review}"
                    file_comment_id = self._post_comment(repo_name, pr_number, review_text, comment_id, comment_type)
                    review_comments.append({"text": review_text, "comment_id": file_comment_id})

            # Handle case with no reviewable files
            if not reviewable_files:
                no_files_text = ("✅ **ReviewBot - No code files to review!**\n\n"
                               "This PR doesn't contain code changes that need review.")
                self._post_comment(repo_name, pr_number, no_files_text, comment_id, comment_type)
                review_comments.append("No reviewable files found for review")

            return review_comments

        except Exception as e:
            return [f"Error reviewing PR: {str(e)}"]

    def _get_ai_review(self, filename: str, patch: str, custom_instruction: str = None) -> str:
        """Get AI review for a code patch"""
        base_prompt = (
            f"Review ONLY the changed lines in this code diff:\n\n"
            f"File: {filename}\n"
            f"Code changes (diff):\n{patch}\n\n"
            "Provide a brief review focusing on:\n"
            "1. Issues in the changed lines only\n"
            "2. Quick suggestions for improvement\n\n"
            "Keep response under 3 sentences. Be concise.\n\n"
            "If you identify issues that need code fixes, end your response with: SUGGEST_FIX"
        )

        if custom_instruction:
            prompt = f"{base_prompt}\n\nAdditional instruction: {custom_instruction}"
        else:
            prompt = base_prompt

        ai_review = self._call_falcon_ai(prompt)
        return ai_review
    
    def _get_ai_summary(self, title: str, description: str, changes: str) -> str:
        """Get AI summary of the entire PR"""
        prompt = (
            f"Summarize this PR in 2-3 sentences:\n\n"
            f"PR Title: {title}\n"
            f"Description: {description}\n\n"
            f"Code Changes:\n{changes[:1000]}\n\n"
            "What does this PR do and any major concerns?"
        )
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
                "messages": [{"role": "user", "content": prompt}]
            }

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

    async def _answer_question(self, pr, question: str) -> str:
        """Answer a specific question about the PR"""
        files_summary = ", ".join([f.filename for f in pr.get_files()][:5])
        if len(list(pr.get_files())) > 5:
            files_summary += "..."

        prompt = (
            "Answer this question about a GitHub PR:\n\n"
            f"Question: {question}\n\n"
            "PR Context:\n"
            f"- Title: {pr.title}\n"
            f"- Description: {pr.body or 'No description'}\n"
            f"- Files changed: {files_summary}\n\n"
            "Provide a direct, helpful answer in 2-3 sentences."
        )

        return self._call_falcon_ai(prompt)

    def _post_comment(self, repo_name: str, pr_number: int, text: str, 
                     comment_id: int = None, comment_type: str = "issue_comment"):
        """Post comment as reply or new comment and return the comment ID"""
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            if comment_id and comment_type == "review_comment":
                try:
                    comment = pr.create_review_comment_reply(comment_id, text)
                    return comment.id
                except Exception as e:
                    print(f"Failed to reply to review comment: {str(e)}")
                    comment = pr.create_issue_comment(text)
                    return comment.id
            else:
                comment = pr.create_issue_comment(text)
                return comment.id

        except Exception as e:
            print(f"Error posting comment: {str(e)}")
            return None