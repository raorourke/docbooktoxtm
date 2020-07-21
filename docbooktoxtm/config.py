import os
import platform
from subprocess import Popen, PIPE

PLATFORM = platform.system()
HOME_DIR = os.path.expanduser('~')

SYSTEM_DEFAULTS = {
    'Linux': os.path.join(HOME_DIR, '.weconfig', 'config.sh'),
    'Windows': os.path.join(HOME_DIR, '.weconfig', 'config.bat')
}

USE_ENVIRONMENT_VARIABLES = 1
DEFAULT_CONFIG_FILE = SYSTEM_DEFAULTS.get(PLATFORM)
GITHUB_TOKEN: str = 'GITHUB_TOKEN_PLACEHOLDER'

if PLATFORM == 'Linux':
    GITHUB_TOKEN = os.environ.get('github_token')
    if GITHUB_TOKEN is None and os.path.exists(DEFAULT_CONFIG_FILE):
        sh_command = f"source {DEFAULT_CONFIG_FILE} && echo $github_token"
        process = Popen(sh_command, shell=True, stdout=PIPE)
        output, error = process.communicate()
        GITHUB_TOKEN = f"{output.decode().strip()}"
        if GITHUB_TOKEN is None:
            USE_ENVIRONMENT_VARIABLES = 0
if PLATFORM == 'Windows':
    GITHUB_TOKEN = os.environ.get('github_token')
    if GITHUB_TOKEN is None and os.path.exists(DEFAULT_CONFIG_FILE):
        cmd_command = f"{DEFAULT_CONFIG_FILE} && call echo %github_token%"
        process = Popen(cmd_command, stdout=PIPE)
        output, error = process.communicate()
        GITHUB_TOKEN = f"{output.decode().strip()}"
