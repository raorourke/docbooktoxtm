import sys
import os
from subprocess import Popen, DEVNULL

USE_ENVIRONMENT_VARIABLES = 1
DEFAULT_CONFIG_FILE = '/$HOME/.weconfig/config.sh'
GITHUB_TOKEN: str = 'GITHUB_TOKEN_PLACEHOLDER'

if USE_ENVIRONMENT_VARIABLES:
    os.system(f'source {DEFAULT_CONFIG_FILE}')
    GITHUB_TOKEN = os.environ.get('github_token')