#!/usr/bin/env python3
#

import os
import shlex
import shutil
import subprocess
import requests
import zipfile
from typing import List, Tuple, Optional, Union

import xmltodict
from github import Github
from lxml import etree
from pydantic import BaseModel

from docbooktoxtm import config


def get_book_info(book_info_file: str = 'Book_Info.xml'):
    with open(book_info_file, 'r') as xml_file:
        return xmltodict.parse(xml_file.read()).get('bookinfo')


def get_book_info_from_zip(zipf: str, path: str = '00-introduction/01-Book_Info.xml'):
    with zipfile.ZipFile(zipf, 'r') as f:
        book_info_file = f.open(os.path.join(f"{f.namelist()[0].split('/', 1)[0]}", path), 'r')
        return xmltodict.parse(book_info_file.read()).get('bookinfo')


def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))


def lists_to_tuple(*args):
    new_list = []
    for arg in args:
        new_list = new_list + arg
    return tuple(new_list)


def ppxml(path):
    for root, dirs, files in os.walk(path):
        for file in files:
            subprocess.call(shlex.split(f'ppxml "./{os.path.join(root, file)}"'))


SUBTITLE_INDEX = {
    'Teilnehmerarbeitsbuch': 'de-DE',
    'Manuel d\'exercices': 'fr-FR',
    '受講生用のワークブック': 'ja-JP',
    '수강생 워크북': 'ko-KR',
    'Livro do aluno': 'pt-BR',
    'Рабочая тетрадь': 'ru-RU',
    '学员练习册': 'zh-CN',
    'Libro de trabajo del estudiante': 'es-ES',
    'छात्र-छात्रा की वर्कबुक': 'hi-IN'
}


class BookInfo(BaseModel):
    productname: str
    edition: int
    invpartnumber: str
    productname: str
    productnumber: str
    pubdate: Optional[str] = None
    pubsnumber: str
    subtitle: Union[str, dict]
    title: str
    subtitle_index: dict = SUBTITLE_INDEX


def get_intro(xml_file, source_dir=None, remaining_files=None, working_list=None):
    remaining_files = remaining_files or []
    working_list = working_list or []
    source_dir = source_dir or os.path.dirname(xml_file)
    parser = etree.XMLParser(recover=True)
    root_file = xml_file if os.path.exists(xml_file) else os.path.join(source_dir, xml_file)
    root = etree.parse(root_file, parser=parser).getroot()
    intro_files = [x for child in root if (x := child.attrib.get('href')) if 'sg-chapters' not in x]
    intro_files = [file for file in intro_files if os.path.exists(os.path.join(source_dir, file))]
    new_remaining_files = intro_files + remaining_files
    new_working_list = working_list
    if intro_files:
        if xml_file in working_list:
            index = working_list.index(xml_file) + 1
            new_working_list[index:index] = intro_files
        else:
            new_working_list = working_list + intro_files
    if new_remaining_files:
        file, *remaining_files = new_remaining_files
        return get_intro(file, source_dir, remaining_files, new_working_list)
    return new_working_list


def get_intro_file_list(intro_files: List[str], source_dir: str = '.', target_dir: str = '.'):
    return [
        (os.path.join(source_dir, file),
         os.path.join(target_dir, f"00-introduction/{i:02d}-{f'/{i:02d}-'.join(file.split('/'))}"))
        for i, file in enumerate(
            intro_files, start=1)
    ]


def get_chapters(xml_file):
    parser = etree.XMLParser(recover=True)
    root = etree.parse(xml_file, parser=parser).getroot()
    return [x for child in root if (x := child.attrib.get('href')) if 'sg-chapters' in x]


def get_chapter_file_list(chapter_list: List[str], source_dir: str = '.', target_dir: str = '.'):
    chapter_file_list = []
    for i, chapter in enumerate(chapter_list, start=1):
        chapter_dir = os.path.join(target_dir, f"{i:02d}-{os.path.basename(chapter).split('.', 1)[0]}/sg-chapters")
        chapter_file_list.append(
            (os.path.join(source_dir, chapter), os.path.join(chapter_dir, f"{i:02d}-{os.path.basename(chapter)}")))
        parser = etree.XMLParser(recover=True)
        root = etree.parse(os.path.join(source_dir, chapter), parser=parser).getroot()
        sections = [x for child in root if (x := child.attrib.get('href'))]
        for j, section in enumerate(sections, start=1):
            chapter_file_list.append(
                (os.path.join(source_dir, 'sg-chapters', section),
                 os.path.join(chapter_dir, os.path.dirname(section), f"{j:02d}-{os.path.basename(section)}"))
            )
    return chapter_file_list


def copy_and_rename(file_list: List[Tuple[str, str]], reverse: bool = False):
    if reverse:
        new_dirs = {os.path.dirname(old) for old, new in file_list}
    else:
        new_dirs = {os.path.dirname(new) for old, new in file_list}
    for directory in new_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
    for old, new in file_list:
        if reverse:
            shutil.copy(new, old)
        else:
            shutil.copy(old, new)


def unsource(source_zip):
    with zipfile.ZipFile(source_zip, 'r') as zipf:
        zip_dir = os.path.join(zipf.namelist()[0].split('/', 1)[0], 'guides/en-US')
        for file in zipf.namelist():
            if zip_dir in file:
                zipf.extract(file)
        shutil.move(zip_dir, '..')
        shutil.rmtree(zipf.namelist()[0].split('/', 1)[0])
    os.remove(source_zip)
    os.chdir('en-US')
    target_dir = './en-US'
    source_dir = '..'
    os.mkdir(target_dir)
    book = BookInfo(**get_book_info())
    toc = f"./{book.invpartnumber}-SG.xml"
    intro_file_list = get_intro_file_list(
        get_intro(toc), source_dir, target_dir
    )
    chapter_file_list = get_chapter_file_list(
        get_chapters(toc), source_dir, target_dir
    )
    file_list = lists_to_tuple(intro_file_list, chapter_file_list)
    copy_and_rename(file_list)
    zip_filename = book.invpartnumber + '-' + book.pubdate + '.zip'
    zipf = zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED)
    zipdir(target_dir, zipf)
    shutil.move(zip_filename, '../..')
    os.chdir('../..')
    shutil.rmtree(target_dir)
    return zip_filename


def resource(source_file, target_file):
    with zipfile.ZipFile(source_file, 'r') as zipf:
        source_dir = os.path.join('.', zipf.namelist()[0].split('/', 1)[0], 'guides/en-US')
        zipf.extractall()
    with zipfile.ZipFile(target_file, 'r') as zipf:
        zipf.extractall()
    target_dir = os.path.join('.', 'en-US')
    ppxml(target_dir)
    book = BookInfo(**get_book_info(os.path.join(source_dir, 'Book_Info.xml')))
    localized_book = BookInfo(**get_book_info(os.path.join(target_dir, '00-introduction/01-Book_Info.xml')))
    toc = os.path.join(source_dir, f"{book.invpartnumber}-SG.xml")
    intro_file_list = get_intro_file_list(get_intro(toc), source_dir, target_dir)
    chapter_file_list = get_chapter_file_list(get_chapters(toc), source_dir, target_dir)
    file_list = lists_to_tuple(intro_file_list, chapter_file_list)
    copy_and_rename(file_list, reverse=True)
    shutil.rmtree(target_dir)
    target_filename = f"{localized_book.invpartnumber}-{localized_book.pubdate}_{localized_book.subtitle_index[localized_book.subtitle]}.zip"
    zipf = zipfile.ZipFile(target_filename, 'w', zipfile.ZIP_DEFLATED)
    zipdir(f"./{source_dir.split('/')[1]}", zipf)
    shutil.rmtree(f"./{source_dir.split('/')[1]}")


def get_latest_release(course: str, user: str = 'RedHatTraining'):
    g = Github(config.token)
    repo = g.get_user(user).get_repo(course)
    return repo.get_latest_release()


def get_zip(release):
    zipball = requests.get(release.zipball_url, headers=config.headers, stream=True)
    course = release.url.split('/', 6)[5]
    fname = course + '-' + release.tag_name + '.zip'
    open(fname, 'wb').write(zipball.content)
    with zipfile.ZipFile(fname, 'r') as bad_zip:
        bad_dir = bad_zip.namelist()[0].split('/')[0]
        bad_zip.extractall()
    os.remove(fname)
    shutil.move(bad_dir, fname.rsplit('.', 1)[0])
    zipf = zipfile.ZipFile(fname, 'w', zipfile.ZIP_DEFLATED)
    zipdir(fname.rsplit('.', 1)[0], zipf)
    shutil.rmtree(fname.rsplit('.', 1)[0])


def get_pdfs(release):
    pdf_name, role_name = [f'{release.url.split("/", 6)[5]}-{release.tag_name}{x}' for x in ['.pdf', '-ROLE.pdf']]
    headers = {'Accept': 'application/octet-stream'}
    headers.update(config.headers)
    for asset in release.get_assets():
        if asset.name in [pdf_name, role_name]:
            r = requests.get(asset.url, headers=headers, stream=True)
            open(asset.name, 'wb').write(r.content)

