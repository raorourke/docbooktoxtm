from lxml import etree
import os, zipfile, re
from iteration_utilities import deepflatten
from itertools import chain
from docbooktoxtm import functions as func

os.chdir('/home/ryan/Documents/tmp/sandbox')
DEFAULT_TARGET = 'en-US'
target_fname = 'RH318_de-DE_fix1.zip'

book = func.BookInfo(**func.get_book_info(target_fname))
source_fname = 'RH318-RHV4.3-en-1-20200501.zip'
bad_target = 'RH318_de-DE.zip'

with zipfile.ZipFile(bad_target, 'r') as f_zip:
    if bool(re.search(r'^[0-9]{2}-[a-z]+.*$', f_zip.namelist()[0].split('/', 1)[0])):
        f_zip.extractall(DEFAULT_TARGET)





'''
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
target_dir = DEFAULT_TARGET_DIR
ppxml(target_dir)
book = BookInfo(
    **get_book_info(
        target_fname,
        '00-introduction/01-Book_Info.xml'
    )
)
toc = os.path.join(
    source_dir,
    f"{book.course}-SG.xml"
)
intro_file_list = get_intro_file_list(
    get_intro_names(toc),
    target_dir,
    os.path.join('.', source_dir)
)
chapter_file_list = get_chapter_file_list(
    get_chapter_names(toc),
    target_dir,
    os.path.join('.', source_dir)
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
resourced_fname = f"{book.course}-{book.pubsnumber}_{book.target}.zip"
with zipfile.ZipFile(resourced_fname, 'w', zipfile.ZIP_DEFLATED) as f_zip:
    zipdir(source_dir.split('/')[0], f_zip)
shutil.rmtree(source_dir.split('/')[0])
os.remove(source_fname)
os.remove(target_fname)
return resourced_fname
'''












'''
course = 'DTX123'
source_dir = os.path.join('.', f"{course}-source/guides/en-US")
toc = f"{course}-SG.xml"
toc_path = os.path.join(source_dir, toc)

parser = etree.XMLParser(recover=True)





def walk_intro_files(top_list, source_dir='.', file_list=None):
    print(f"{top_list=}")
    file_list = file_list or []
    print(f"{file_list=}")
    for file in top_list:
        print(f"{file=}")
        file_list.append((file, source_dir, '00-introduction'))
        file_path = os.path.join(source_dir, file)
        root = etree.parse(file_path, parser=parser).getroot()
        child_files = [child_file for child in root if (
            (child_file := child.attrib.get('href'))
            and
            os.path.exists(os.path.join(source_dir, child_file))
            )
        ]
        if len(child_files) > 0:
            file_list += walk_intro_files(child_files, source_dir)
            print(f"{file_list=}")
    return file_list
'''
def walk_intro_files(file_list, source_dir='.', output_list=None):
    output_list = output_list or []
    if len(file_list) == 0:
        return output_list
    else:
        file = file_list[0]
        output_list.append((file, source_dir, '00-introduction'))
        file_path = os.path.join(source_dir, file)
        root = etree.parse(file_path, parser=parser).getroot()
        child_files = [child_file for child in root if (
            (child_file := child.attrib.get('href'))
            and
            os.path.exists(os.path.join(source_dir, child_file))
        )]
        if len(child_files) > 0:
            output_list += walk_intro_files(child_files, source_dir)
        return walk_intro_files(file_list[1:], source_dir, output_list)



'''
root = etree.parse(toc_path, parser=parser).getroot()
intro_files = walk_intro_files([file for child in root if (
    (file := child.attrib.get('href'))
    and
    'sg-chapters' not in file
)], source_dir)
chapters = [chapter for child in root if (
    (chapter := child.attrib.get('href'))
    and
    'sg-chapters' in chapter
    and
    'appendix' not in chapter
)]
appendices = [appendix for child in root if (
    (appendix := child.attrib.get('href'))
    and
    'appendix' in appendix
)]
'''


