from code_review_system import CodeReviewSystem


async def main():

    system = CodeReviewSystem()

    # 处理特定的PR
    result = await system.process_pr(repo_name="your_username/your_repo", pr_number=123)

    print("\nComplete Results:")
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
