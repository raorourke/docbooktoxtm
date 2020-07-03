#!/usr/bin/env python3

import os
import re
import shutil
import zipfile
from pathlib import Path
from subprocess import Popen, DEVNULL
from typing import List, Optional, Any, TypeVar, IO, Union

import requests
import xmltodict
from fuzzywuzzy import process, fuzz
from github import Github
from lxml import etree
from pydantic import BaseModel

from docbooktoxtm.config import GITHUB_TOKEN

HEADERS: dict = {'Authorization': f"token {GITHUB_TOKEN}"}
DEFAULT_TARGET = 'en-US'
DEFAULT_TARGET_DIR = os.path.join('.', DEFAULT_TARGET)

FileName = TypeVar('FileName', str, IO, Path)


def zipdir(path: Path,
           f_zip: zipfile.ZipFile
           ) -> None:
    for root, _, files in os.walk(path):
        for file in files:
            f_zip.write(os.path.join(root, file))


def lists_to_tuple(*args: list) -> tuple:
    new_list = []
    for arg in args:
        new_list += arg
    return tuple(new_list)


def get_zip(course: str,
            release_tag: str = None,
            user: str = 'RedHatTraining',
            token: str = GITHUB_TOKEN
            ) -> FileName:
    g = Github(token)
    repo = g.get_user(user).get_repo(course)
    releases = [
        release
        for release in repo.get_releases()
        if (
                release_tag in release.target_commitish
                or
                release_tag in release.tag_name
        )
    ] if release_tag else list(repo.get_releases())
    if len(releases) == 1:
        release = releases[0]
    else:
        release = sorted(
            releases,
            key=lambda x: x.published_at,
            reverse=True
        )[0]
    if release_tag is None:
        latest_release = repo.get_latest_release()
        if latest_release != release:
            release_tags = {release.tag_name.split('-')[-4] for release in [release, latest_release]}
            if len(release_tags) > 1:
                release = sorted(
                    [release, latest_release],
                    key=lambda x: x.tag_name.split('-')[-4],
                    reverse=True
                )[0]
            else:
                release = sorted(
                    [release, latest_release],
                    key=lambda x: x.published_at,
                    reverse=True
                )[0]
    zipball = requests.get(release.zipball_url, headers=HEADERS, stream=True)
    course = release.url.split('/', 6)[5]
    fname = f"{course}-{release.tag_name}.zip"
    with open(fname, 'wb') as f_zip:
        f_zip.write(zipball.content)
    with zipfile.ZipFile(fname, 'r') as bad_zip:
        bad_dir = bad_zip.namelist()[0].split('/')[0]
        bad_zip.extractall()
    os.remove(fname)
    shutil.move(bad_dir, fname.rsplit('.', 1)[0])
    with zipfile.ZipFile(fname, 'w', zipfile.ZIP_DEFLATED) as f_zip:
        zipdir(fname.rsplit('.', 1)[0], f_zip)
    shutil.rmtree(fname.rsplit('.', 1)[0])
    return fname
