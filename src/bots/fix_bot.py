import os
import requests
import re
import json
from github import Github, Auth
from dotenv import load_dotenv


class FixBot:
    def __init__(self):
        load_dotenv()
        auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
        self.github = Github(auth=auth)
        self.falcon_api_key = os.getenv("FALCON_API_KEY")
        self.base_url = "https://falconai.planview-prod.io"

    async def fix_code(
        self,
        repo_name: str,
        pr_number: int,
        review_comments: list,
        custom_instruction: str = None,
        comment_id: int = None,
        comment_type: str = "issue_comment",
    ):
        """Generate AI-powered fixes as GitHub suggested changes"""
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            fixes_applied = []

            # If there's a custom instruction and comment_id, decide whether to fix or answer
            if custom_instruction and comment_id:
                should_fix = await self._should_provide_fix(custom_instruction)
                
                if should_fix:
                    # Treat as fix request - analyze PR for fixes
                    fix_result = await self._analyze_pr_for_fixes(
                        repo, pr, custom_instruction, custom_instruction, comment_id, comment_type
                    )
                    # Also post inline reply acknowledging the fix request
                    self._post_comment(
                        repo_name,
                        pr_number,
                        f"🔧 **FixBot:** Working on your request: '{custom_instruction}' - Check the code suggestions above!",
                        comment_id,
                        comment_type,
                    )
                    return [fix_result]
                else:
                    # Treat as question - provide answer
                    response = await self._answer_question(pr, custom_instruction, comment_id)
                    self._post_comment(
                        repo_name,
                        pr_number,
                        f"🤖 **FixBot:**\n{response}",
                        comment_id,
                        comment_type,
                    )
                    return [f"Direct response: {response}"]

            # Otherwise, process review comments for fixes
            for comment in review_comments:
                if isinstance(comment, str):
                    if "🤖" in comment and "AI Summary:" not in comment:
                        fix_result = await self._create_suggested_fix(
                            repo,
                            pr,
                            comment,
                            custom_instruction,
                            comment_id,
                            comment_type,
                        )
                    else:
                        fix_result = await self._analyze_pr_for_fixes(
                            repo,
                            pr,
                            comment,
                            custom_instruction,
                            comment_id,
                            comment_type,
                        )

                    if fix_result and "Created" in fix_result:
                        fixes_applied.append(fix_result)

            if not fixes_applied:
                self._post_comment(
                    repo_name,
                    pr_number,
                    "🤖 **FixBot** ✅\n\nCode looks good! No issues found that require fixes.",
                    comment_id,
                    comment_type,
                )
                return ["No fixes needed - posted positive feedback"]

            return fixes_applied
        except Exception as e:
            return [f"Error creating fixes: {str(e)}"]

    async def _create_suggested_fix(
        self,
        repo,
        pr,
        review_comment,
        custom_instruction: str = None,
        comment_id: int = None,
        comment_type: str = "issue_comment",
    ):
        """Create GitHub suggested change for the fix"""
        try:
            filename = self._extract_filename(review_comment)
            if not filename:
                return "Could not identify file to fix"

            file_patch = self._get_file_patch(pr, filename)
            if not file_patch:
                return f"Could not find changes for {filename}"

            fixes = await self._generate_partial_fixes(
                review_comment, file_patch, custom_instruction
            )
            suggestions_created = self._create_suggestions(
                pr, fixes, filename, file_patch
            )

            if suggestions_created > 0:
                summary_text = f"🤖 **FixBot Analysis for {filename}**\n\n✅ Created {suggestions_created} suggestions"
                self._post_comment(
                    repo.name, pr.number, summary_text, comment_id, comment_type
                )

            return f"Created {suggestions_created} suggestions for {filename}"
        except Exception as e:
            return f"Error: {str(e)}"

    def _extract_filename(self, review_comment: str) -> str:
        """Extract filename from review comment"""
        patterns = [
            r"🤖 ([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+):",
            r"([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+):",
            r"`([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)`",
            r"([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)",
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

    def _create_suggestions(
        self, pr, fixes: list, filename: str, file_patch: str
    ) -> int:
        """Create GitHub suggestions for all fixes"""
        suggestions_created = 0

        print(f"DEBUG: Processing {len(fixes)} fixes for {filename}")
        for i, fix in enumerate(fixes):
            print(
                f"DEBUG: Fix {i+1} - Confidence: {fix['confidence']}, Issue: {fix['issue']}"
            )

            confidence_emoji = (
                "🟢"
                if fix["confidence"] >= 0.9
                else "🟡" if fix["confidence"] >= 0.7 else "🔴"
            )
            guidance = self._get_guidance(fix["confidence"])

            try:
                pr.create_review_comment(
                    body=f"""🔧 **FixBot Suggestion #{i+1}** {confidence_emoji}

```suggestion
{fix['code']}
```

**Confidence:** {fix['confidence']:.0%} | **Issue:** {fix['issue']}

{guidance}""",
                    commit=pr.head.sha,
                    path=filename,
                    line=fix.get("line", self._get_line_from_patch(file_patch)),
                )
                suggestions_created += 1
                print(f"DEBUG: Successfully created suggestion {i+1}")
            except Exception as e:
                print(f"DEBUG: Failed to create suggestion {i+1}: {str(e)}")

        return suggestions_created

    def _get_guidance(self, confidence: float) -> str:
        """Get acceptance guidance based on confidence"""
        if confidence >= 0.9:
            return "✅ **Recommended** - High confidence, safe to apply"
        elif confidence >= 0.8:
            return "⚠️ **Review suggested** - Good confidence, please verify"
        elif confidence >= 0.7:
            return (
                "🔍 **Manual review required** - Moderate confidence, check carefully"
            )
        else:
            return "⚠️ **Low confidence** - Please review carefully before applying"

    def _post_comment(
        self,
        repo_name: str,
        pr_number: int,
        text: str,
        comment_id: int = None,
        comment_type: str = "issue_comment",
    ):
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
                headers={
                    "Authorization": f"Bearer {self.falcon_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=90,
            )

            if response.status_code == 200:
                result = response.json()
                if "choices" in result and result["choices"]:
                    return result["choices"][0]["message"]["content"].strip()

            return f"API error {response.status_code}"
        except Exception as e:
            return f"Falcon AI failed: {str(e)}"

    async def _generate_partial_fixes(
        self, review_comment: str, file_patch: str, custom_instruction: str = None
    ) -> list:
        """Generate multiple targeted fixes with confidence scores"""
        prompt = f"""Analyze this code review and create targeted fixes:

Review: {review_comment}
Diff: {file_patch}

Provide ONLY a valid JSON array with this exact format (no markdown, no backticks in values):
[{{"issue": "Brief description", "code": "Fixed code lines", "confidence": 0.95, "line": 10}}]

IMPORTANT: 
- Return ONLY the JSON array, no other text
- Do NOT use backticks or markdown in the "code" field
- Put actual fixed code in the "code" field as plain text
- Confidence: 0.0-1.0 scale"""

        if custom_instruction:
            prompt += f"\n\nAdditional instruction: {custom_instruction}"

        try:
            response = self._call_falcon_ai(prompt)
            print(f"DEBUG: AI Response: {response[:200]}...")

            # Clean up the response to extract JSON
            json_str = response.strip()
            
            # Remove markdown code blocks if present
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", json_str)
            if json_match:
                json_str = json_match.group(1).strip()
            
            # Find JSON array in the response
            array_match = re.search(r"(\[.*\])", json_str, re.DOTALL)
            if array_match:
                json_str = array_match.group(1)

            fixes = json.loads(json_str)
            print(f"DEBUG: Parsed {len(fixes)} fixes from AI")

            valid_fixes = []
            for fix in fixes:
                if isinstance(fix, dict) and "code" in fix and "confidence" in fix:
                    valid_fixes.append(
                        {
                            "issue": fix.get("issue", "Code improvement"),
                            "code": fix["code"].strip(),
                            "confidence": min(max(fix["confidence"], 0.0), 1.0),
                            "line": fix.get("line"),
                        }
                    )

            # Sort by confidence (highest first) and limit to top 3
            valid_fixes.sort(key=lambda x: x['confidence'], reverse=True)
            print(f"DEBUG: Created {len(valid_fixes)} valid fixes, returning top 3")
            return valid_fixes[:3]
        except Exception as e:
            print(f"DEBUG: Exception in _generate_partial_fixes: {str(e)}")
            return [
                {
                    "issue": "Code improvement",
                    "code": "# TODO: Address code review feedback",
                    "confidence": 0.5,
                }
            ]

    async def _analyze_pr_for_fixes(
        self,
        repo,
        pr,
        instruction: str,
        custom_instruction: str = None,
        comment_id: int = None,
        comment_type: str = "issue_comment",
    ):
        """Analyze entire PR for fixes when directly mentioned"""
        try:
            files = list(pr.get_files())
            fixes_created = 0

            for file in files:
                if file.patch and any(
                    file.filename.endswith(ext)
                    for ext in [".py", ".js", ".ts", ".java", ".cpp", ".go"]
                ):
                    synthetic_review = f"🤖 {file.filename}: {instruction}"
                    fix_result = await self._create_suggested_fix(
                        repo, pr, synthetic_review, custom_instruction
                    )
                    if fix_result and "Created" in fix_result:
                        fixes_created += 1

            return (
                f"Analyzed PR: processed {fixes_created} files"
                if fixes_created > 0
                else "No fixable issues found"
            )
        except Exception as e:
            return f"Error analyzing PR: {str(e)}"

    async def _should_provide_fix(self, instruction: str) -> bool:
        """Use AI to decide if instruction requires code fixes or just an answer"""
        prompt = f"""Analyze this user instruction carefully:

Instruction: {instruction}

Respond with ONLY "FIX" or "ANSWER".

FIX = User wants actual code changes, implementations, or modifications
ANSWER = User is asking questions, seeking opinions, or wants explanations

Examples:
- "fix the SQL injection" -> FIX
- "add error handling" -> FIX
- "remove this function" -> FIX
- "do you think this can be committed?" -> ANSWER
- "why is this bad?" -> ANSWER
- "what does this code do?" -> ANSWER
- "should I merge this?" -> ANSWER"""
        
        try:
            response = self._call_falcon_ai(prompt)
            return "FIX" in response.upper()
        except:
            return False  # Default to answer if AI fails
    
    async def _answer_question(self, pr, question: str, comment_id: int = None) -> str:
        """Answer a specific question about the PR with comment context"""
        files_summary = ", ".join([f.filename for f in pr.get_files()][:5])
        if len(list(pr.get_files())) > 5:
            files_summary += "..."

        # Get comment context if comment_id is provided
        comment_context = ""
        if comment_id:
            print(f"DEBUG: Fetching context for comment_id: {comment_id}")
            try:
                # Try to get the parent comment for context
                repo_obj = pr.base.repo
                comment = repo_obj.get_issue_comment(comment_id)
                comment_context = f"\n\nComment Context (user is asking about this comment):\n- Author: {comment.user.login}\n- Comment: {comment.body[:300]}"
                print(f"DEBUG: Got issue comment context: {comment.body[:50]}...")
            except Exception as e:
                print(f"DEBUG: Issue comment failed: {str(e)}")
                try:
                    # Try as review comment
                    comment = pr.get_review_comment(comment_id)
                    comment_context = f"\n\nComment Context (user is asking about this review comment):\n- Author: {comment.user.login}\n- File: {comment.path}\n- Comment: {comment.body[:300]}"
                    print(f"DEBUG: Got review comment context: {comment.body[:50]}...")
                except Exception as e2:
                    print(f"DEBUG: Review comment failed: {str(e2)}")
                    comment_context = "\n\nNote: User is responding to a specific comment but context unavailable."

        prompt = f"""Answer this question about a GitHub PR:

Question: {question}

PR Context:
- Title: {pr.title}
- Description: {pr.body or 'No description'}
- Files changed: {files_summary}{comment_context}

If the question is vague (like "why", "how", "what") and you have comment context, answer about that specific comment. If no context is available, ask for clarification about what specifically they want to know. Keep response conversational and helpful, 1-2 sentences max."""

        return self._call_falcon_ai(prompt)

    def _get_line_from_patch(self, patch: str) -> int:
        """Extract line number from patch"""
        match = re.search(r"@@\s*-\d+,?\d*\s*\+?(\d+)", patch)
        return int(match.group(1)) if match else 1
