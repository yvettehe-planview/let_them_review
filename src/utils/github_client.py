import os
from github import Github
from dotenv import load_dotenv

load_dotenv()

class GitHubClient:
    def __init__(self, token=None):
        self.token = token or os.getenv('GITHUB_TOKEN')
        self.client = Github(self.token)
    
    def get_pr(self, repo_name, pr_number):
        repo = self.client.get_repo(repo_name)
        return repo.get_pull(pr_number)
    
    def get_pr_files(self, repo_name, pr_number):
        pr = self.get_pr(repo_name, pr_number)
        return list(pr.get_files())
    
    def add_review_comment(self, repo_name, pr_number, body, path, line):
        pr = self.get_pr(repo_name, pr_number)
        pr.create_review_comment(body, pr.head.sha, path, line)