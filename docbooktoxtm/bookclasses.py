import os
import re
import shutil
import zipfile
from collections import namedtuple
from pathlib import Path
from typing import TypeVar, Iterable, Tuple, Union, Any, Optional

import xmltodict
from fuzzywuzzy import process, fuzz
from lxml import etree
from pydantic import BaseModel, FilePath, DirectoryPath

DEFAULT_SOURCE_ROOT = os.path.join('guides', 'en-US')
DEFAULT_TARGET_ROOT = 'en-US'

PathPair = TypeVar('PathPair', bound=Tuple[DirectoryPath, DirectoryPath])
FileList = TypeVar('FileList', bound=Iterable[PathPair])
BookFile = namedtuple('BookFile', ['chapter', 'count', 'file', 'path'])


def ppxml(path: str) -> None:
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


def zipdir(path: Path,
           f_zip: zipfile.ZipFile
           ) -> None:
    for root, _, files in os.walk(path):
        for file in files:
            f_zip.write(os.path.join(root, file))


class BookFile:
    def __init__(self, chapter, count, file_path):
        self.chapter = chapter
        self.count = f"{count:02d}"
        self.name = os.path.basename(file_path)
        self.path = os.path.dirname(file_path)

    def source_path(self, source_root):
        return os.path.join(source_root, self.path, self.name)

    def target_path(self, target_root=DEFAULT_TARGET_ROOT):
        return os.path.join(target_root, self.chapter, self.path, f"{self.count}-{self.name}")


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
    productname: str = None
    edition: Union[int, str] = None
    invpartnumber: str = None
    productnumber: str = None
    pubdate: str = None
    pubsnumber: str = None
    subtitle: str = None
    title: str = None
    target: str = None
    course: str = None
    release_tag: str = None

    def __init__(self, **info: Any):
        super().__init__(**info)
        if self.pubsnumber is None:
            if self.pubdate is not None:
                object.__setattr__(self, 'pubsnumber', self.pubdate)
            else:
                object.__setattr__(self, 'pubsnumber', '12345678')
        if not re.search(r'^[A-Z]+?$', self.productname):
            self.productname = ''.join(letter for letter in self.productname if letter.isupper())
        if isinstance(self.edition, str):
            self.edition = int(''.join(i for i in self.edition if i.isdigit()))
        self.target = self.get_book_language(self.subtitle)
        self.course = self.invpartnumber
        self.release_tag = f"{self.productname}{self.productnumber}-en-{self.edition}-{self.pubsnumber}"

    @staticmethod
    def _xmltodict(zip_fname: FilePath):
        with zipfile.ZipFile(zip_fname, 'r') as f_zip:
            bi_files = [file for file in f_zip.namelist() if 'Book_Info.xml' in file]
            if len(bi_files) == 1:
                bi_file = f_zip.open(bi_files[0], 'r')
            elif len(bi_files) > 1:
                filtered_bi_files = [file for file in bi_files if 'en-US' in file]
                if len(filtered_bi_files) == 1:
                    bi_file = f_zip.open(filtered_bi_files[0], 'r')
            else:
                raise ValueError
            book = xmltodict.parse(bi_file.read()).get('bookinfo')
        return {attr: value.get('#text') if '#text' in value else value for attr, value in book.items()}

    @staticmethod
    def get_book_language(query: str):
        return SUBTITLE_INDEX.get(
            process.extractOne(
                query,
                list(SUBTITLE_INDEX.keys()),
                scorer=fuzz.ratio)[0]
        )

    @classmethod
    def from_zipf(cls, zipf):
        info = cls._xmltodict(zipf)
        return cls(**info)


class Book(BookInfo):
    source_zip: str
    target_zip: Optional[str] = None
    mapf: str
    source_root: str
    target_root: str = DEFAULT_TARGET_ROOT
    intro: tuple
    appendices: tuple
    chapters: tuple
    files: tuple = None
    flist: tuple = None
    clean: tuple = None

    def __init__(self,
                 source_zip: str,
                 target_zip: Optional[str] = None
                 ):
        book_info = self._xmltodict(target_zip) if target_zip else self._xmltodict(source_zip)
        attributes = self.__get_attributes(source_zip)
        super().__init__(source_zip=source_zip, target_zip=target_zip, **attributes, **book_info)
        files = [BookFile('00-introduction', i, file) for i, file in enumerate(self.intro, start=1)]
        files += self.__get_chapter_file_list()
        files += self.__get_appendix_file_list()
        self.files = tuple(files)
        self.flist = tuple(
            (file.source_path(self.source_root), file.target_path(self.target_root)) for file in self.files)
        if target_zip:
            self.clean = self.__get_clean_flist()

    def __get_clean_flist(self):
        with zipfile.ZipFile(self.target_zip, 'r') as f_zip:
            zip_files = [file for file in f_zip.namelist() if file[-1] != '/']
            clean = tuple((dest_path, orig_path) if (
                    dest_path.split('/', 1)[1] in zip_files
            ) else (
                self._get_alt_file(
                    dest_path,
                    zip_files
                ),
                orig_path
            ) for orig_path, dest_path in self.flist)
        return clean

    def __get_attributes(self, source_zip):
        def get_book(zipf: zipfile.ZipFile, fname: str, source_root: str):
            namelist = [file for file in zipf.namelist() if file[-1] != '/']
            root_file = zipf.open(os.path.join(source_root, fname))
            parser = etree.XMLParser(recover=True)
            root = etree.parse(root_file, parser=parser).getroot()
            children = [file for child in root if (
                    (file := child.attrib.get('href'))
                    and
                    os.path.join(source_root, file) in namelist
            )
                        ]
            file_list = []
            for child in children:
                file_list.append(child)
                file_list += get_book(zipf, child, source_root)
            return file_list

        with zipfile.ZipFile(source_zip, 'r') as f_zip:
            sg = [file for file in f_zip.namelist() if re.search(r'^.*/guides/en-US/.*-SG\.xml$', file)]
            source_root, mapf = os.path.split(sg[0])
            book_tree = get_book(f_zip, mapf, source_root)
            intro = tuple(file for file in book_tree if 'sg-chapters' not in file)
            appendices = tuple(file for file in book_tree if 'appendix' in file)
            chapters = tuple(file for file in book_tree if ('sg-chapters' in file and file not in appendices))

        return {
            'mapf': mapf,
            'source_root': source_root,
            'intro': intro,
            'appendices': appendices,
            'chapters': chapters
        }

    def __get_chapter_file_list(self):
        chapter_files = []
        with zipfile.ZipFile(self.source_zip) as f_zip:
            for i, chapter in enumerate(self.chapters, start=1):
                chapter_root, chapter_fname = os.path.split(chapter)
                chapter_open = f_zip.open(os.path.join(self.source_root, chapter))
                chapter_index = f"{i:02d}-{chapter_fname.split('.', 1)[0]}"
                root = etree.parse(chapter_open, parser=etree.XMLParser(recover=True)).getroot()
                sections = [section for child in root if (section := child.attrib.get('href'))]
                chapter_file = BookFile(chapter_index, i, chapter)
                chapter_files.append(chapter_file)
                chapter_files += [BookFile(chapter_index, j, os.path.join(chapter_root, section)) for j, section in
                                  enumerate(sections, start=1)]
        return chapter_files

    def __get_appendix_file_list(self):
        appendix_files = []
        j = 1
        with zipfile.ZipFile(self.source_zip) as f_zip:
            for i, appendix in enumerate(self.appendices, start=1):
                appendix_root, appendix_fname = os.path.split(appendix)
                appendix_open = f_zip.open(os.path.join(self.source_root, appendix))
                root = etree.parse(appendix_open, parser=etree.XMLParser(recover=True)).getroot()
                sections = [section for child in root if (section := child.attrib.get('href'))]
                appendix_file = BookFile('99-appendix', i, appendix)
                appendix_files.append(appendix_file)
                for section in sections:
                    appendix_files.append(BookFile('99-appendix', j, os.path.join(appendix_root, section)))
                    j += 1
        return appendix_files

    def _get_alt_file(self, missing_file: FilePath, zip_files: list):
        fname = missing_file.rsplit('/', 1)[1].split('-', 1)[1]
        chapter = missing_file.split('/')[1]
        query_files = [file for file in zip_files if (
                fname in file
                and
                chapter in file
        )]
        return os.path.join(self.target_root,
                            process.extractOne(missing_file, query_files, scorer=fuzz.token_set_ratio)[0])

    def __call__(self, working_dir: str = '.', reverse: bool = False):
        flist = self.clean if reverse else self.flist
        from_root, to_root = self.source_root.split('/')[0], self.target_root.split('/')[0]
        if reverse:
            from_root, to_root = to_root, from_root
            ppxml(from_root)
        if self.target_zip:
            with zipfile.ZipFile(self.target_zip, 'r') as target_zip:
                if target_zip.namelist()[0].split('/')[0] != self.target_root:
                    target_zip.extractall(os.path.join(working_dir, self.target_root))
                else:
                    target_zip.extractall()
        with zipfile.ZipFile(self.source_zip, 'r') as source_zip:
            source_zip.extractall()
        for current, new in flist:
            if not os.path.exists(os.path.dirname(new)):
                os.makedirs(os.path.dirname(new))
            shutil.move(current, new)
        if reverse:
            for root, dirs, files in os.walk(os.path.join(to_root, 'guides')):
                for dir in dirs:
                    if (dir != 'en-US' and dir in SUBTITLE_INDEX):
                        shutil.rmtree(os.path.join(root, dir))
            shutil.copytree(os.path.join(to_root, 'guides', 'en-US'), os.path.join(to_root, 'guides', self.target))
            shutil.rmtree(os.path.join(to_root, 'guides', 'en-US'))
        zip_fname = f"{self.course}-{self.pubsnumber}_{self.target}.zip"
        with zipfile.ZipFile(zip_fname, 'w', zipfile.ZIP_DEFLATED) as f_zip:
            zipdir(to_root, f_zip)
        shutil.rmtree(from_root)
        shutil.rmtree(to_root)
        os.remove(self.source_zip)
        if self.target_zip:
            os.remove(self.target_zip)
        return zip_fname
