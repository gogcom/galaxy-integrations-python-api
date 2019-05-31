import os
import sys
from galaxy.github.exporter import transfer_repo

GITHUB_USERNAME = "goggalaxy"
GITHUB_EMAIL = "galaxy-sdk@gog.com"
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO_NAME = "galaxy-integrations-python-api"
SOURCE_BRANCH = os.environ["GIT_REFSPEC"]

GITLAB_USERNAME = "galaxy-client"
GITLAB_REPO_NAME = "galaxy-plugin-api"

def version_provider(_):
    return sys.argv[1]

gh_version = transfer_repo(
    version_provider=version_provider,
    source_repo_spec="git@gitlab.gog.com:{}/{}.git".format(GITLAB_USERNAME, GITLAB_REPO_NAME),
    source_include_elements=["src", "tests", "requirements.txt", ".gitignore", "*.md", "pytest.ini", "setup.py"],
    source_branch=SOURCE_BRANCH,
    dest_repo_spec="https://{}:{}@github.com/{}/{}.git".format(GITHUB_USERNAME, GITHUB_TOKEN, "gogcom", GITHUB_REPO_NAME),
    dest_branch="master",
    dest_user_email=GITHUB_EMAIL,
    dest_user_name="GOG Galaxy SDK Team"
)