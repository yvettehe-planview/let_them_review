import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bots.review_bot import ReviewBot
from bots.fix_bot import FixBot


# 使用示例
class CodeReviewSystem:
    def __init__(self):
        self.review_bot = ReviewBot()
        self.fix_bot = FixBot()

    async def process_pr(self, repo_name: str, pr_number: int):
        """处理完整的PR review和fix流程"""
        print(f"Processing PR #{pr_number} in {repo_name}")

        # 1. Review PR
        print("Reviewing PR...")
        review_comments = await self.review_bot.review_pr(repo_name, pr_number)
        print(f"Review completed with {len(review_comments)} comments")

        # 2. Generate and apply fixes
        print("Generating fixes...")
        fixes = await self.fix_bot.fix_code(repo_name, pr_number, review_comments)
        print(f"Created {len(fixes)} fix PRs")

        return {"review_comments": review_comments, "fixes": fixes}
