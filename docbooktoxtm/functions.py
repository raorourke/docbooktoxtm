#!/usr/bin/env python3
#

import os
import shutil
import zipfile
from collections import OrderedDict
from subprocess import Popen, DEVNULL
from typing import List, Tuple, Optional, Union, Iterable, Any, NewType

import requests
import xmltodict
from github import Github
from lxml import etree
from pydantic import BaseModel

GITHUB_TOKEN: str = os.environ.get('github_token')
HEADERS: dict = {'Authorization': f"token {GITHUB_TOKEN}"}

DEFAULT_TARGET = 'en-US'
DEFAULT_TARGET_DIR = os.path.join('.', DEFAULT_TARGET)

BookStr = NewType('BookStr', Optional[Union[str, dict]])
BookInt = NewType('BookInt', Optional[Union[int, dict]])
FileName = NewType('FileName', str)
FilePath = NewType('FilePath', str)
Directory = NewType('Directory', str)
FileList = NewType(
    'FileList',
    Iterable[
        Union[
            Tuple[FileName, FileName],
            Tuple[FilePath, FilePath],
            FileName,
            FilePath
        ]
    ]
)


def get_book_info(zip_fname: FileName,
                  path: str = '00-introduction/01-Book_Info.xml'
                  ) -> OrderedDict:
    with zipfile.ZipFile(zip_fname, 'r') as f_zip:
        book_info_file = f_zip.open(
            os.path.join(
                f"{f_zip.namelist()[0].split('/', 1)[0]}",
                path
            ), 'r'
        )
        return xmltodict.parse(book_info_file.read()).get('bookinfo')


def zipdir(path: Directory,
           f_zip: zipfile.ZipFile
           ) -> None:
    for root, _, files in os.walk(path):
        for file in files:
            f_zip.write(os.path.join(root, file))


def lists_to_tuple(*args: Union[list, FileList]) -> tuple:
    new_list = []
    for arg in args:
        new_list = new_list + arg
    return tuple(new_list)


def ppxml(path: Directory) -> None:
    for root, _, files in os.walk(path):
        for file in files:
            file = os.path.join(root, file)
            cmd1 = f'mv "{file}" "{file}.bak" 2>&1'
            cmd2 = f'xmllint --format --recover "{file}.bak" > "{file}" 2>&1'
            cmd3 = f'rm -f "{file}.bak" 2>&1'
            pattern = r'/^\..*\.xml\.bak.*parser error.*not defined$/,+2d'
            cmd4 = f'sed "{pattern}" -i {file}'
            final = Popen(f"{cmd1}; {cmd2}; {cmd3}; {cmd4}", shell=True, stdin=DEVNULL,
                          stdout=DEVNULL, stderr=DEVNULL, close_fds=True)
            final.communicate()


SUBTITLE_INDEX = {
    'Teilnehmerarbeitsbuch': 'de-DE',
    'Manuel d\'exercices': 'fr-FR',
    '受講生用のワークブック': 'ja-JP',
    '受講生用ワークブック': 'ja-JP',
    '수강생 워크북': 'ko-KR',
    'Livro do aluno': 'pt-BR',
    'Рабочая тетрадь': 'ru-RU',
    '学员练习册': 'zh-CN',
    'Libro de trabajo del estudiante': 'es-ES',
    'छात्र-छात्रा की वर्कबुक': 'hi-IN',
    'Student Workbook': 'en-US'
}


class BookInfo(BaseModel):
    productname: BookStr = None
    edition: BookInt = None
    invpartnumber: BookStr = None
    productnumber: BookStr = None
    pubdate: BookStr = None
    pubsnumber: BookStr = None
    subtitle: BookStr = None
    title: BookStr = None
    target: BookStr = None

    def __init__(self, **info: Any):
        super().__init__(**info)
        if self.pubsnumber is None:
            if self.pubdate is not None:
                object.__setattr__(self, 'pubsnumber', self.pubdate)
            else:
                object.__setattr__(self, 'pubsnumber', '12345678')
        self.target = SUBTITLE_INDEX[self.subtitle]
        self.course = self.invpartnumber
        self.release_tag = f"{self.productname}{self.productnumber}" if (
            self.productname and self.productnumber
        ) else None


def get_intro_names(fname: Union[FileName, FilePath],
                    source_dir: Directory = None,
                    remaining_files: List[FileName] = None,
                    working_list: List[FileName] = None
                    ) -> FileList:
    remaining_files = remaining_files or []
    working_list = working_list or []
    source_dir = source_dir or os.path.dirname(fname)
    parser = etree.XMLParser(recover=True)
    root_file = fname if os.path.exists(fname) else os.path.join(source_dir, fname)
    root = etree.parse(
        root_file,
        parser=parser
    ).getroot()
    intro_files = [
        file
        for child in root
        if (
                (file := child.attrib.get('href'))
                and
                'sg-chapters' not in file
                and
                os.path.exists(os.path.join(source_dir, file))
        )
    ]
    new_remaining_files = intro_files + remaining_files
    new_working_list = working_list
    if intro_files:
        if fname in working_list:
            index = working_list.index(fname) + 1
            new_working_list[index:index] = intro_files
        else:
            new_working_list = working_list + intro_files
    if new_remaining_files:
        file, *remaining_files = new_remaining_files
        return get_intro_names(file, source_dir, remaining_files, new_working_list)
    return FileList(new_working_list)


def get_intro_file_list(intro_files: FileList,
                        target_dir: Directory = None,
                        source_dir: Directory = None
                        ) -> FileList:
    target_dir = target_dir or '.'
    source_dir = source_dir or '.'
    return FileList([
        (
            FilePath(os.path.join(
                source_dir,
                file
            )),
            FilePath(os.path.join(
                target_dir,
                '00-introduction',
                *[f"{i:02d}-{part}" for part in file.split('/')]
            ))
        )
        for i, file in enumerate(intro_files, start=1)
    ])


def get_chapter_names(fname: Union[FileName, FilePath]) -> FileList:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(
        fname,
        parser=parser
    ).getroot()
    return FileList([
        chapter
        for child in root
        if (
                (chapter := child.attrib.get('href'))
                and
                'sg-chapters' in chapter
        )
    ])


def get_chapter_file_list(chapter_list: FileList,
                          target_dir: Directory = None,
                          source_dir: Directory = None
                          ) -> FileList:
    target_dir = target_dir or '.'
    source_dir = source_dir or '.'
    chapter_file_list = []
    for i, chapter in enumerate(chapter_list, start=1):
        chapter_dir = os.path.join(
            target_dir,
            f"{i:02d}-{os.path.basename(chapter).split('.', 1)[0]}",
            'sg-chapters'
        )
        chapter_file_list.append(
            (
                os.path.join(
                    source_dir,
                    chapter
                ),
                os.path.join(
                    chapter_dir,
                    f"{i:02d}-{os.path.basename(chapter)}"
                )
            )
        )
        parser = etree.XMLParser(recover=True)
        root = etree.parse(
            os.path.join(source_dir, chapter),
            parser=parser
        ).getroot()
        sections = [
            section
            for child in root
            if (
                    (section := child.attrib.get('href')) is not None
            )
        ]
        for j, section in enumerate(sections, start=1):
            chapter_file_list.append(
                (
                    FilePath(os.path.join(
                        source_dir,
                        'sg-chapters',
                        section
                    )),
                    FilePath(os.path.join(
                        chapter_dir,
                        os.path.dirname(section),
                        f"{j:02d}-{os.path.basename(section)}"
                    ))
                )
            )
    return FileList(chapter_file_list)


def copy_and_rename(file_list: FileList,
                    reverse: bool = False
                    ) -> None:
    if reverse:
        dossiers = {os.path.dirname(old) for old, new in file_list}
    else:
        dossiers = {os.path.dirname(new) for old, new in file_list}
    for dossier in dossiers:
        if not os.path.exists(dossier):
            os.makedirs(dossier)
    for old, new in file_list:
        if reverse:
            shutil.copy(new, old)
        else:
            shutil.copy(old, new)


def unsource(source_fname: FileName) -> FileName:
    with zipfile.ZipFile(source_fname, 'r') as f_zip:
        zip_dir = os.path.join(
            f_zip.namelist()[0].split('/', 1)[0],
            'guides/en-US'
        )
        for file in f_zip.namelist():
            if zip_dir in file:
                f_zip.extract(file)
        shutil.move(zip_dir, '.')
        shutil.rmtree(f_zip.namelist()[0].split('/', 1)[0])
    book = BookInfo(
        **get_book_info(
            source_fname,
            'guides/en-US/Book_Info.xml'
        )
    )
    os.remove(source_fname)
    os.chdir(DEFAULT_TARGET_DIR)
    target_dir = Directory(DEFAULT_TARGET_DIR)
    os.mkdir(target_dir)
    toc = FilePath(f"./{book.course}-SG.xml")
    intro_file_list = get_intro_file_list(
        get_intro_names(toc), target_dir
    )
    chapter_file_list = get_chapter_file_list(
        get_chapter_names(toc), target_dir
    )
    file_list = lists_to_tuple(intro_file_list, chapter_file_list)
    copy_and_rename(file_list)
    zip_fname = FileName(f"{book.course}-{book.pubsnumber}.zip")
    with zipfile.ZipFile(zip_fname, 'w', zipfile.ZIP_DEFLATED) as f_zip:
        zipdir(target_dir, f_zip)
    shutil.move(zip_fname, '..')
    os.chdir('..')
    shutil.rmtree(target_dir)
    return zip_fname


def resource(source_fname: FileName,
             target_fname: FileName
             ) -> FileName:
    with zipfile.ZipFile(source_fname, 'r') as f_zip:
        source_dir = os.path.join(
            f_zip.namelist()[0].split('/', 1)[0],
            'guides'
        )
        for file in f_zip.namelist():
            if source_dir in file:
                f_zip.extract(file)
    with zipfile.ZipFile(target_fname, 'r') as f_zip:
        f_zip.extractall()
    source_dir = os.path.join(source_dir, DEFAULT_TARGET)
    target_dir = Directory(DEFAULT_TARGET_DIR)
    ppxml(target_dir)
    book = BookInfo(
        **get_book_info(
            target_fname,
            '00-introduction/01-Book_Info.xml'
        )
    )
    toc = FilePath(os.path.join(
        source_dir,
        f"{book.course}-SG.xml"
    ))
    intro_file_list = get_intro_file_list(
        get_intro_names(toc),
        target_dir,
        Directory(os.path.join('.', source_dir))
    )
    chapter_file_list = get_chapter_file_list(
        get_chapter_names(toc),
        target_dir,
        Directory(os.path.join('.', source_dir))
    )
    file_list = lists_to_tuple(intro_file_list, chapter_file_list)
    copy_and_rename(file_list, reverse=True)
    shutil.rmtree(target_dir)
    shutil.move(
        source_dir,
        os.path.join(
            source_dir.rsplit('/', 1)[0],
            book.target
        )
    )
    for target in SUBTITLE_INDEX.values():
        if all([
            target != book.target,
            os.path.exists(
                os.path.join(
                    source_dir.rsplit('/', 1)[0],
                    target
                )
            )
        ]):
            shutil.rmtree(
                os.path.join(
                    source_dir.rsplit('/', 1)[0],
                    target
                )
            )
    resourced_fname = FileName(f"{book.course}-{book.pubsnumber}_{book.target}.zip")
    with zipfile.ZipFile(resourced_fname, 'w', zipfile.ZIP_DEFLATED) as f_zip:
        zipdir(Directory(source_dir.split('/')[0]), f_zip)
    shutil.rmtree(source_dir.split('/')[0])
    os.remove(source_fname)
    os.remove(target_fname)
    return resourced_fname


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
        if release_tag in release.target_commitish
    ] if release_tag else [
        release
        for release in repo.get_releases()
    ]
    if len(releases) == 1:
        release = releases[0]
    else:
        release = sorted(
            releases,
            key=lambda x: x.published_at,
            reverse=True
        )[0]
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
    fname = FileName(f"{course}-{release.tag_name}.zip")
    with open(fname, 'wb') as f_zip:
        f_zip.write(zipball.content)
    with zipfile.ZipFile(fname, 'r') as bad_zip:
        bad_dir = bad_zip.namelist()[0].split('/')[0]
        bad_zip.extractall()
    os.remove(fname)
    shutil.move(bad_dir, fname.rsplit('.', 1)[0])
    with zipfile.ZipFile(fname, 'w', zipfile.ZIP_DEFLATED) as f_zip:
        zipdir(Directory(fname.rsplit('.', 1)[0]), f_zip)
    shutil.rmtree(fname.rsplit('.', 1)[0])
    return fname