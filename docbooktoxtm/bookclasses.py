import logging
import os
import re
import shutil
import zipfile
from pathlib import Path
from subprocess import Popen, PIPE
from typing import Iterable, Tuple, Union, Any, Optional

import xmltodict
from fuzzywuzzy import process, fuzz
from lxml import etree
from pydantic import BaseModel, DirectoryPath

from docbooktoxtm.config import PLATFORM

DEFAULT_SOURCE_ROOT = os.path.join('guides', 'en-US')
DEFAULT_TARGET_ROOT = Path('en-US')

PathPair = Tuple[DirectoryPath, DirectoryPath]
FileList = Iterable[PathPair]


def ppxml(
        path: Path
) -> None:
    logging.debug("Running xmllint on files.")
    for root, _, files in os.walk(path):
        for file in files:
            file = os.path.join(root, file)
            cmd1 = f'mv "{file}" "{file}.bak" 2>&1'
            cmd2 = f'xmllint --format --recover "{file}.bak" > "{file}" 2>&1'
            cmd3 = f'rm -f "{file}.bak" 2>&1'
            pattern = r'/^.*xml.bak.*parser error.*not defined$/,+2d'
            cmd4 = f'sed "{pattern}" -i {file}'
            final = Popen(
                f"{cmd1}; {cmd2}; {cmd3}; {cmd4}",
                shell=True,
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                close_fds=True
            )
            output, error = final.communicate()
            logging.debug(f"{file=}")
            logging.debug(f"{output=}")
            logging.debug(f"{error=}")


def zipdir(
        path: Path,
        f_zip: zipfile.ZipFile
) -> None:
    for path_obj in path.iterdir():
        if path_obj.is_dir():
            f_zip.write(f"{path_obj}")
            zipdir(path_obj, f_zip)
        if path_obj.is_file():
            f_zip.write(f"{path_obj}")


class BookFile:
    def __init__(
            self,
            chapter: str,
            count: int,
            file_path: Path,
            target_root: Path = DEFAULT_TARGET_ROOT,
            target_override: Path = None
    ):
        self.chapter = chapter
        self.count = f"{count:02d}"
        self.path = file_path
        self.target_root = target_root
        self.subdir = Path('/'.join(file_path.parts[file_path.parts.index('en-US') + 1:-1]))
        self.target_override = target_override

    @classmethod
    def from_BookFile(cls, book_file, target_override):
        return cls(
            book_file.chapter,
            int(book_file.count),
            book_file.path,
            book_file.target_root,
            target_override
        )

    @property
    def source_path(self):
        return Path.cwd() / self.path

    @property
    def target_path(self):
        if self.target_override:
            return Path.cwd() / self.target_override
        if self.chapter == '00-introduction':
            return Path.cwd() / self.target_root / self.chapter / self.name
        return Path.cwd() / self.target_root / self.chapter / self.subdir / self.name

    @property
    def basename(self):
        return self.path.name

    @property
    def name(self):
        return f"{self.count}-{self.path.name}"

    @property
    def parts(self):
        return self.path.parts[:-1]

    @property
    def parent(self):
        return self.path.parent

    def unsource(self):
        try:
            self.source_path.rename(self.target_path)
        except FileNotFoundError:
            self.target_path.parent.mkdir(parents=True, exist_ok=True)
            self.source_path.rename(self.target_path)

    def resource(self):
        try:
            self.target_path.rename(self.source_path)
        except FileNotFoundError:
            self.source_path.parent.mkdir(parents=True, exist_ok=True)
            self.target_path.rename(self.source_path)


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
            logging.info(f"{bi_files=}")
            logging.info(f"{len(bi_files)=}")
            if len(bi_files) == 1:
                if '00-01' in bi_files[0]:
                    raise TypeError
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
        try:
            info = cls._xmltodict(zipf)
            return cls(**info)
        except TypeError:
            root = DEFAULT_TARGET_ROOT
            print(root)
            with zipfile.ZipFile(zipf, 'r') as target_zip:
                target_zip.extractall(f"{root}")
            os.remove(zipf)
            intro = root / '00-introduction'
            for f in intro.iterdir():
                if f.is_file():
                    f.replace(f.with_name(f.name[3:]))
            for chapter in root.iterdir():
                if chapter.is_dir() and chapter.name[:2] != '00':
                    chapter_index, chapter_name = chapter.name.split('-', 1)
                    chapter_path = root / chapter.name / 'sg-chapters' / 'topics' / chapter_name
                    chapter_path.mkdir(parents=True, exist_ok=True)
                    for f in chapter.iterdir():
                        if f.is_file():
                            if f.name[:2] == '00':
                                new_index = root / chapter.name / 'sg-chapters' / f"{chapter_index}-{f.name.split('-', 1)[1]}"
                                f.rename(new_index)
                            else:
                                new_path = chapter_path / f.name
                                f.rename(new_path)
            with zipfile.ZipFile(zipf, 'w', zipfile.ZIP_DEFLATED) as f_zip:
                zipdir(root, f_zip)
            shutil.rmtree(f"{root}")
            info = cls._xmltodict(zipf)
            return cls(**info)


class Book(BookInfo):
    source_zip: str
    target_zip: Optional[str] = None
    wd: str
    mapf: str
    source_root: Path
    target_root: Path = DEFAULT_TARGET_ROOT
    intro: tuple
    appendices: tuple
    chapters: tuple
    files: Optional[tuple] = None
    flist: Optional[Union[tuple, list]] = None
    clean: Optional[Union[tuple, list]] = None
    path_clean: Optional[Union[tuple, list]] = None
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
        files = [
            BookFile('00-introduction', i, file)
            for i, file in enumerate(self.intro, start=1)
        ]
        files += self.__get_chapter_file_list()
        files += self.__get_appendix_file_list()
        self.files = tuple(files)
        self.flist = tuple(
            (file.source_path, file.target_path) for file in self.files
        )
        if target_zip:
            self.target_actuals = self.__get_target_actuals()

    def __get_target_actuals(self):
        with zipfile.ZipFile(self.target_zip, 'r') as f_zip:
            flist = [f for f in f_zip.namelist() if f[-1] != '/']
            if flist[0].split('/', 1)[0] != 'en-US':
                return tuple(Path(f"en-US/{f}") for f in flist)
            return tuple(Path(f) for f in flist)

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

    def __path_clean(self):
        clean = []
        for f in self.files:
            if f.target_path.exists():
                clean.append(f)
            else:
                bests = process.extractBests(
                    f.name,
                    (
                        f"{tf}"
                        for tf in self.target_actuals
                        if (
                            f.basename in f"{tf}"
                            and f.chapter in f"{tf}"
                        )
                    )
                )
                if bests:
                    best = BookFile.from_BookFile(f, bests[0][0])
                    clean.append(best)
        self.path_clean = clean

    @staticmethod
    def __get_attributes(course, source_zip):
        def get_book(zipf: zipfile.ZipFile, fname: str, source_root: str):
            namelist = [file for file in zipf.namelist() if file[-1] != '/']
            root_file = zipf.open('/'.join((source_root, fname)))
            parser = etree.XMLParser(recover=True, resolve_entities=False)
            root = etree.parse(root_file, parser=parser).getroot()
            children = [
                file for child in root if (
                        (file := child.attrib.get('href'))
                        and '/'.join((source_root, file)) in namelist
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
            intro = tuple(
                Path(f"{source_root}/{file}")
                for file in book_tree
                if 'sg-chapters' not in file
            )
            appendices = tuple(
                Path(f"{source_root}/{file}")
                for file in book_tree
                if 'appendix' in file
            )
            chapters = tuple(
                Path(f"{source_root}/{file}")
                for file in book_tree
                if (
                        'sg-chapters' in file
                        and 'appendix' not in file
                )
            )

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
        def get_content_sections(root):
            filelist = []
            children = [child for child in root]
            for child in children:
                if file := child.attrib.get('href'):
                    filelist.append(file)
                filelist.extend(get_content_sections(child))
            return set(filelist)

        chapter_files = []
        with zipfile.ZipFile(self.source_zip) as f_zip:
            for i, chapter in enumerate(self.chapters, start=1):
                chapter_open = f_zip.open(f"{chapter}")
                chapter_index = f"{i:02d}-{chapter.stem}"
                root = etree.parse(
                    chapter_open,
                    parser=etree.XMLParser(recover=True, resolve_entities=False)
                ).getroot()
                root_sections = tuple(
                    chapter.parent / section
                    for child in root
                    if (section := child.attrib.get('href'))
                )
                sections = []
                for section in root_sections:
                    sections.append(section)
                    section_open = f_zip.open(f"{section}")
                    root = etree.parse(
                        section_open,
                        parser=etree.XMLParser(recover=True, resolve_entities=False)
                    ).getroot()
                    if (
                            content_files := set(
                                section.parent / content_section
                                for content_section in get_content_sections(root)
                                if '..' not in content_section
                            )
                    ):
                        sections += content_files
                chapter_files.append(
                    BookFile(chapter_index, i, chapter)
                )
                chapter_files += [
                    BookFile(
                        chapter_index,
                        j,
                        section
                    ) for j, section in enumerate(sections, start=1)
                ]
        return chapter_files

    def __get_appendix_file_list(self):
        def get_content_sections(root):
            filelist = []
            children = [child for child in root]
            for child in children:
                if file := child.attrib.get('href'):
                    filelist.append(file)
                filelist.extend(get_content_sections(child))
            return set(filelist)

        appendix_files = []
        j = 1
        with zipfile.ZipFile(self.source_zip) as f_zip:
            for i, appendix in enumerate(self.appendices, start=1):
                appendix_open = f_zip.open(f"{appendix}")
                root = etree.parse(
                    appendix_open,
                    parser=etree.XMLParser(recover=True, resolve_entities=False)
                ).getroot()
                appendices = [
                    appendix.parent / section
                    for child in root
                    if (section := child.attrib.get('href'))
                ]
                appendix_file = BookFile('99-appendix', i, appendix)
                appendix_files.append(appendix_file)
                for appendix_section in appendices:
                    appendix_files.append(
                        BookFile('99-appendix', j, appendix_section)
                    )
                    j += 1
                    appendix_section_open = f_zip.open(f"{appendix_section}")
                    root = etree.parse(
                        appendix_section_open,
                        parser=etree.XMLParser(recover=True, resolve_entities=False)
                    ).getroot()
                    if (
                            content_files := set(
                                appendix_section.parent / content_section
                                for content_section in get_content_sections(root)
                                if '..' not in content_section
                            )
                    ):
                        for content_file in content_files:
                            appendix_files.append(
                                BookFile(
                                    '99-appendix', j, content_file
                                )
                            )
                            j += 1
        return appendix_files

    def unzip_source(self):
        with zipfile.ZipFile(self.source_zip, 'r') as source_zip:
            zip_files = source_zip.namelist()
            source_root = Path(zip_files[0].split('/')[0])
            for zipf in zip_files:
                if f"{source_root}/guides" in zipf:
                    source_zip.extract(zipf)
        os.remove(self.source_zip)
        for path in Path(f"{source_root}/guides").iterdir():
            if path.is_dir() and path.name != 'en-US':
                shutil.rmtree(path)
        return source_root

    def unzip_target(self, format=False):
        with zipfile.ZipFile(self.target_zip, 'r') as target_zip:
            if target_zip.namelist()[0].split('/')[0] != f"{self.target_root}":
                target_zip.extractall(f"{self.target_root}")
            else:
                target_zip.extractall()
        os.remove(self.target_zip)
        if PLATFORM == 'Linux' and format:
            ppxml(self.target_root)
        return self.target_root

    def resource(self):
        sfdir = self.unzip_source()
        tfdir = self.unzip_target(format=True)
        self.__path_clean()
        if len(self.files) != len(self.path_clean):
            expected = tuple(f.path for f in self.files)
            actual = tuple(f.path for f in self.path_clean)
            if len(self.files) > len(self.path_clean):
                missing_files = {f for f in expected if f not in actual}
                for missing_file in missing_files:
                    logging.warning(f"Source file not found in target files: {missing_file}")
        for f in self.path_clean:
            f.resource()
        shutil.rmtree(tfdir)
        if self.target != 'en-US':
            shutil.copytree(sfdir / 'guides' / 'en-US', sfdir / 'guides' / self.target)
            shutil.rmtree(sfdir / 'guides' / 'en-US')
        zip_fname = f"{self.course}-{self.pubsnumber}_{self.target}.zip"
        with zipfile.ZipFile(zip_fname, 'w', zipfile.ZIP_DEFLATED) as f_zip:
            zipdir(sfdir, f_zip)
        shutil.rmtree(sfdir)
        return zip_fname

    def unsource(self):
        sfdir = self.unzip_source()
        tfdir = self.target_root
        for f in self.files:
            f.unsource()
        shutil.rmtree(sfdir)
        zip_fname = f"{self.course}-{self.pubsnumber}_{self.target}.zip"
        with zipfile.ZipFile(zip_fname, 'w', zipfile.ZIP_DEFLATED) as f_zip:
            zipdir(tfdir, f_zip)
        shutil.rmtree(tfdir)
        return zip_fname

    def __call__(self):
        return self.resource() if self.target_zip else self.unsource()
