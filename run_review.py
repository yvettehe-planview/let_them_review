#!/usr/bin/env python3
"""
GitHub Action runner for AI code review bot
Usage: python run_review.py <repo_name> <pr_number>
"""
import asyncio
import sys
import os
from src.core.code_review_system import CodeReviewSystem

async def main():
    if len(sys.argv) != 3:
        print("Usage: python run_review.py <repo_name> <pr_number>")
        sys.exit(1)
    
    repo_name = sys.argv[1]
    pr_number = int(sys.argv[2])
    
    print(f"🤖 Starting AI review for {repo_name} PR #{pr_number}")
    
    system = CodeReviewSystem()
    result = await system.process_pr(repo_name, pr_number)
    
    print(f"✅ Review completed!")
    print(f"📝 {len(result['review_comments'])} review comments posted")
    print(f"🔧 {len(result['fixes'])} fix suggestions posted")

if __name__ == "__main__":
    asyncio.run(main())