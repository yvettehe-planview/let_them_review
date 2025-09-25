import asyncio
from src.bots.review_bot import ReviewBot
from src.bots.fix_bot import FixBot

async def trigger_bot(bot_name: str, instruction: str, repo_name: str = None, pr_number: int = None, comment_id: int = None, comment_type: str = "issue_comment"):
    """
    Trigger a specific bot with custom instruction
    
    Args:
        bot_name: "review" or "fix"
        instruction: Custom instruction for the bot
        repo_name: GitHub repo (format: "owner/repo")
        pr_number: PR number to process
    
    Returns:
        dict: Result of bot execution
    """
    try:
        if bot_name.lower() == "review":
            bot = ReviewBot()
            if repo_name and pr_number:
                result = await bot.review_pr(repo_name, pr_number, custom_instruction=instruction, comment_id=comment_id, comment_type=comment_type)
            else:
                result = {"error": "ReviewBot requires repo_name and pr_number"}
        
        elif bot_name.lower() == "fix":
            bot = FixBot()
            if repo_name and pr_number:
                # Get existing review comments and apply custom instruction
                result = await bot.fix_code(repo_name, pr_number, [instruction], custom_instruction=instruction, comment_id=comment_id, comment_type=comment_type)
            else:
                result = {"error": "FixBot requires repo_name and pr_number"}
        
        else:
            result = {"error": f"Unknown bot: {bot_name}. Use 'review' or 'fix'"}
        
        return {"bot": bot_name, "instruction": instruction, "result": result}
    
    except Exception as e:
        return {"error": f"Bot trigger failed: {str(e)}"}

# Sync wrapper for non-async environments
def run_bot(bot_name: str, instruction: str, repo_name: str = None, pr_number: int = None, comment_id: int = None, comment_type: str = "issue_comment"):
    """Synchronous wrapper for trigger_bot"""
    return asyncio.run(trigger_bot(bot_name, instruction, repo_name, pr_number, comment_id, comment_type))

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Trigger AI bots for code review')
    parser.add_argument('--bot_name', required=True, choices=['review', 'fix'], help='Bot to trigger')
    parser.add_argument('--instruction', required=True, help='Custom instruction for the bot')
    parser.add_argument('--repo_name', required=True, help='Repository (owner/repo)')
    parser.add_argument('--pr_number', required=True, type=int, help='PR number')
    parser.add_argument('--comment_id', type=int, help='Comment ID to reply to')
    parser.add_argument('--comment_type', choices=['issue_comment', 'review_comment'], default='issue_comment', help='Type of comment')
    
    args = parser.parse_args()
    
    result = run_bot(args.bot_name, args.instruction, args.repo_name, args.pr_number, args.comment_id, args.comment_type)
    print(result)