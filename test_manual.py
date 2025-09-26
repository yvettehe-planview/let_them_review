import asyncio
from src.core.code_review_system import CodeReviewSystem


async def test_pr():
    # Test the actual PR
    repo_name = "Yarui-planview/Demo-project-for-hackathon-planview"
    pr_number = 13

    print(f"🤖 Testing bot on {repo_name} PR #{pr_number}")

    system = CodeReviewSystem()
    result = await system.process_pr(repo_name, pr_number)

    print("\n" + "=" * 50)
    print("REVIEW RESULTS:")
    print("=" * 50)
    for comment in result["review_comments"]:
        print(f"📝 {comment}")

    print("\nFIX RESULTS:")
    print("=" * 50)
    for fix in result["fixes"]:
        print(f"🔧 {fix}")


if __name__ == "__main__":
    asyncio.run(test_pr())
