import os
import sys
from galaxy.github.exporter import transfer_repo

GITHUB_USERNAME = "FriendsOfGalaxy"
GITHUB_EMAIL = "friendsofgalaxy@gmail.com"
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO_NAME = "galaxy-plugin-api"
SOURCE_BRANCH = os.environ["GIT_REFSPEC"]

GITLAB_USERNAME = "galaxy-client"
GITLAB_REPO_NAME = "galaxy-plugin-api"

def version_provider():
    return sys.argv[1]

gh_version = transfer_repo(
    version_provider=version_provider,
    source_repo_spec="git@gitlab.gog.com:{}/{}.git".format(GITLAB_USERNAME, GITLAB_REPO_NAME),
    source_include_elements=["src", "tests", "requirements.txt", ".gitignore", "*.md", "pytest.ini"],
    source_branch=SOURCE_BRANCH,
    dest_repo_spec="https://{}:{}@github.com/{}/{}.git".format(GITHUB_USERNAME, GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_REPO_NAME),
    dest_branch="master",
    dest_user_email=GITHUB_EMAIL,
    dest_user_name=GITLAB_USERNAME
)