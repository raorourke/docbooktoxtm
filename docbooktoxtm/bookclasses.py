import logging
import os
import re
import shutil
import zipfile
from os import PathLike
from subprocess import Popen, PIPE
from typing import Iterable, Tuple, Union, Any, Optional

import xmltodict
from fuzzywuzzy import process, fuzz
from lxml import etree
from pydantic import BaseModel, DirectoryPath

from docbooktoxtm.config import PLATFORM

DEFAULT_SOURCE_ROOT = os.path.join('guides', 'en-US')
DEFAULT_TARGET_ROOT = 'en-US'

PathPair = Tuple[DirectoryPath, DirectoryPath]
FileList = Iterable[PathPair]


def ppxml(path: PathLike) -> None:
    logging.debug("Running xmllint on files.")
    for root, _, files in os.walk(path):
        for file in files:
            file = os.path.join(root, file)
            cmd1 = f'mv "{file}" "{file}.bak" 2>&1'
            cmd2 = f'xmllint --format --recover "{file}.bak" > "{file}" 2>&1'
            cmd3 = f'rm -f "{file}.bak" 2>&1'
            pattern = r'/^.*xml.bak.*parser error.*not defined$/,+2d'
            cmd4 = f'sed "{pattern}" -i {file}'
            final = Popen(f"{cmd1}; {cmd2}; {cmd3}; {cmd4}", shell=True, stdin=PIPE,
                          stdout=PIPE, stderr=PIPE, close_fds=True)
            output, error = final.communicate()
            logging.debug(f"{file=}")
            logging.debug(f"{output=}")
            logging.debug(f"{error=}")


def zipdir(path: PathLike,
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
        return os.path.join(*source_root.split('/'), *self.path.split('/'), self.name)

    def target_path(self, target_root=DEFAULT_TARGET_ROOT):
        if self.path == 'Common':
            return os.path.join(target_root, self.chapter, f"{self.count}-{self.name}")
        return os.path.join(*target_root.split('/'), self.chapter, *self.path.split('/'), f"{self.count}-{self.name}")


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
    'Student Workbook': 'en-US',
    'Příručka pro studenty': 'cs-CZ'
}


class BookInfo(BaseModel):
    productname: Optional[str] = None
    edition: Optional[Union[int, str]] = None
    invpartnumber: Optional[str] = None
    productnumber: Optional[str] = None
    pubdate: Optional[str] = None
    pubsnumber: Any = None
    subtitle: Optional[str] = None
    title: Optional[str] = None
    target: Optional[str] = None
    course: Optional[str] = None
    release_tag: Optional[str] = None

    def __init__(self, **info: Any):
        super().__init__(**info)
        if self.pubsnumber is None:
            if self.pubdate is not None:
                object.__setattr__(self, 'pubsnumber', self.pubdate)
            else:
                object.__setattr__(self, 'pubsnumber', '12345678')
        if self.productname is not None and not re.search(r'^[A-Z]+?$', self.productname):
            self.productname = ''.join(letter for letter in self.productname if letter.isupper())
        if isinstance(self.edition, str):
            self.edition = int(''.join(i for i in self.edition if i.isdigit()))
        self.target = self.get_book_language(self.subtitle) if self.subtitle is not None else 'en-US'
        self.course = self.invpartnumber
        self.release_tag = f"{self.productname}{self.productnumber}-en-{self.edition}-{self.pubsnumber}"

    @staticmethod
    def _xmltodict(zip_fname: str):
        with zipfile.ZipFile(zip_fname, 'r') as f_zip:
            bi_files = [file for file in f_zip.namelist() if 'Book_Info.xml' in file]
            if len(bi_files) == 1:
                bi_file = f_zip.open(bi_files[0], 'r')
            elif len(bi_files) > 1:
                filtered_bi_files = [file for file in bi_files if 'en-US' in file]
                if len(filtered_bi_files) == 1:
                    bi_file = f_zip.open(filtered_bi_files[0], 'r')
            else:
                raise ValueError(f"No 'Book_Info.xml' file found in {zip_fname}.")
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
    wd: str
    mapf: str
    source_root: str
    target_root: str = DEFAULT_TARGET_ROOT
    intro: tuple
    appendices: tuple
    chapters: tuple
    files: Optional[tuple] = None
    flist: Optional[Union[tuple, list]] = None
    clean: Optional[Union[tuple, list]] = None
    target_actuals: Optional[Union[tuple, list]] = None
    sublog: Optional[dict] = None

    def __init__(self,
                 source_zip: str,
                 target_zip: Optional[str] = None
                 ):
        book_info = self._xmltodict(target_zip) if target_zip else self._xmltodict(source_zip)
        book_info = self.__validate_book_info(book_info)
        logging.debug(f"Book info extracted from {source_zip}.")
        for key, value in book_info.items():
            logging.debug(f"{key}: {value}")
        attributes = self.__get_attributes(book_info.get('invpartnumber'), source_zip)
        super().__init__(source_zip=source_zip, target_zip=target_zip, wd=os.getcwd(), **attributes, **book_info)
        files = [BookFile('00-introduction', i, file) for i, file in enumerate(self.intro, start=1)]
        files += self.__get_chapter_file_list()
        files += self.__get_appendix_file_list()
        self.files = tuple(files)
        self.flist = tuple(
            (file.source_path(self.source_root), file.target_path(self.target_root)) for file in self.files
        )
        if target_zip:
            self.target_actuals = self.__get_target_actuals()
            self.clean = self.__get_clean_flist()

    def __get_target_actuals(self):
        with zipfile.ZipFile(self.target_zip, 'r') as f_zip:
            flist = [f for f in f_zip.namelist() if f[-1] != '/']
            if flist[0].split('/', 1)[0] != 'en-US':
                return tuple(os.path.join('en-US', *f.split('/')) for f in flist)
            return tuple(os.path.join(*f.split('/')) for f in flist)

    @staticmethod
    def __validate_book_info(info):
        pubdate = info.get('pubdate')
        pubsnumber = info.get('pubsnumber')
        if isinstance(pubdate, str) and not isinstance(pubsnumber, str):
            pubsnumber = pubdate
        if isinstance(pubsnumber, str) and not isinstance(pubdate, str):
            pubdate = pubsnumber
        if isinstance(pubsnumber, str) and isinstance(pubdate, str):
            pubdate = int(pubdate)
            pubsnumber = int(pubsnumber)
            currentdate = str(max(pubdate, pubsnumber))
            pubdate = currentdate
            pubsnumber = currentdate
        info.update({
            'pubdate': pubdate,
            'pubsnumber': pubsnumber
        })
        return info

    def __get_clean_flist(self):
        clean = []
        matches = []
        fdict = {tfname: sfname for sfname, tfname in self.flist}
        for tf in self.target_actuals:
            if tf in fdict:
                clean.append((tf, fdict.get(tf)))
                matches.append(fdict.get(tf))
                logging.info(f"File matched as expected: {tf} -> {fdict.get(tf)}")
            else:
                bests = process.extractBests(tf, (tarf for tarf in fdict if (
                        os.path.basename(fdict.get(tarf)) in tf and fdict.get(tarf) not in matches)))
                if bests:
                    clean.append((tf, fdict.get(bests[0][0])))
                    matches.append(fdict.get(bests[0][0]))
                    logging.info(f"Unexpected filename: {tf}")
                    logging.info(f"Matched to source file: {tf} -> {fdict.get(bests[0][0])}")
                else:
                    logging.warning(f"Unmatched target file: {tf}")
        unmatched_sf = tuple(sf for sf, tf in self.flist if sf not in matches)
        for sf in unmatched_sf:
            logging.warning(f"Source file not found in target files: {sf}")
        return sorted(tuple(clean))

    @staticmethod
    def __get_attributes(course, source_zip):
        def get_book(zipf: zipfile.ZipFile, fname: str, source_root: str):
            namelist = [file for file in zipf.namelist() if file[-1] != '/']
            root_file = zipf.open('/'.join((source_root, fname)))
            parser = etree.XMLParser(recover=True, resolve_entities=False)
            root = etree.parse(root_file, parser=parser).getroot()
            children = [file for child in root if (
                    (file := child.attrib.get('href'))
                    and
                    '/'.join((source_root, file)) in namelist
            )
                        ]
            file_list = []
            for child in children:
                file_list.append(child)
                file_list += get_book(zipf, child, source_root)
            return file_list

        with zipfile.ZipFile(source_zip, 'r') as f_zip:
            root_file_pattern = f"^.*/guides/en-US/{course}-SG\.xml$"
            sg = [file for file in f_zip.namelist() if re.search(root_file_pattern, file)]
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
            'chapters': chapters,
            'clean': [],
            'flist': [],
            'target_actuals': [],
            'sublog': {}
        }

    def __get_chapter_file_list(self):
        chapter_files = []
        with zipfile.ZipFile(self.source_zip) as f_zip:
            for i, chapter in enumerate(self.chapters, start=1):
                chapter_root, chapter_fname = os.path.split(chapter)
                chapter_open = f_zip.open('/'.join((self.source_root, chapter)))
                chapter_index = f"{i:02d}-{chapter_fname.split('.', 1)[0]}"
                root = etree.parse(chapter_open,
                                   parser=etree.XMLParser(recover=True, resolve_entities=False)).getroot()
                sections = [section for child in root if (section := child.attrib.get('href'))]
                chapter_file = BookFile(chapter_index, i, chapter)
                chapter_files.append(chapter_file)
                chapter_files += [BookFile(chapter_index, j, '/'.join((chapter_root, section))) for j, section in
                                  enumerate(sections, start=1)]
        return chapter_files

    def __get_appendix_file_list(self):
        appendix_files = []
        j = 1
        with zipfile.ZipFile(self.source_zip) as f_zip:
            for i, appendix in enumerate(self.appendices, start=1):
                appendix_root = os.path.dirname(appendix)
                appendix_open = f_zip.open('/'.join((self.source_root, appendix)))
                root = etree.parse(appendix_open,
                                   parser=etree.XMLParser(recover=True, resolve_entities=False)).getroot()
                sections = [section for child in root if (section := child.attrib.get('href'))]
                appendix_file = BookFile('99-appendix', i, appendix)
                appendix_files.append(appendix_file)
                for section in sections:
                    appendix_files.append(BookFile('99-appendix', j, '/'.join((appendix_root, section))))
                    j += 1
        return appendix_files

    def unzip_source(self):
        with zipfile.ZipFile(self.source_zip, 'r') as source_zip:
            source_root = source_zip.namelist()[0].split('/')[0]
            source_zip.extractall()
        os.remove(self.source_zip)
        return source_root

    def unzip_target(self):
        with zipfile.ZipFile(self.target_zip, 'r') as target_zip:
            if target_zip.namelist()[0].split('/')[0] != self.target_root:
                target_zip.extractall(self.target_root)
            else:
                target_zip.extractall()
        os.remove(self.target_zip)
        if PLATFORM == 'Linux':
            ppxml(self.target_root)
        return self.target_root

    def resource(self):
        sfdir = self.unzip_source()
        tfdir = self.unzip_target()
        for current, new in self.clean:
            if not os.path.exists(os.path.dirname(new)):
                logging.debug(f"mkdir -p {new}")
                os.makedirs(os.path.dirname(new))
            logging.debug(f"cp {current} {new}")
            shutil.move(current, new)
        shutil.rmtree(tfdir)
        for root, dirs, _ in os.walk(os.path.join(sfdir, 'guides')):
            for d in dirs:
                if d != 'en-US' and d in tuple(SUBTITLE_INDEX.values()):
                    shutil.rmtree(os.path.join(root, d))
        if self.target != 'en-US':
            shutil.copytree(os.path.join(sfdir, 'guides', 'en-US'), os.path.join(sfdir, 'guides', self.target))
            shutil.rmtree(os.path.join(sfdir, 'guides', 'en-US'))
        zip_fname = f"{self.course}-{self.pubsnumber}_{self.target}.zip"
        with zipfile.ZipFile(zip_fname, 'w', zipfile.ZIP_DEFLATED) as f_zip:
            zipdir(sfdir, f_zip)
        shutil.rmtree(sfdir)
        return zip_fname

    def unsource(self):
        sfdir = self.unzip_source()
        tfdir = self.target_root
        os.mkdir(tfdir)
        for current, new in self.flist:
            if not os.path.exists(os.path.dirname(new)):
                logging.debug(f"mkdir -p {new}")
                os.makedirs(os.path.dirname(new))
            logging.debug(f"cp {current} {new}")
            shutil.move(current, new)
        shutil.rmtree(sfdir)
        zip_fname = f"{self.course}-{self.pubsnumber}_{self.target}.zip"
        with zipfile.ZipFile(zip_fname, 'w', zipfile.ZIP_DEFLATED) as f_zip:
            zipdir(tfdir, f_zip)
        shutil.rmtree(tfdir)
        return zip_fname

    def __call__(self):
        return self.resource() if self.target_zip else self.unsource()
