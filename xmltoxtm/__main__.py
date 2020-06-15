import sys

from xmltoxtm.functions import resource, unsource, BookInfo, get_book_info, get_zip, FileName


def resource_cli(target_fname: FileName) -> FileName:
    """
    This function restores the XML source files to their original structure, as
    well as restores any files that had been removed from scope during prep.
    :param target_fname: Name of target .ZIP package. This file will
     be processed in current working directory.
    :return target_file: Name of target restructured .ZIP package.
    """
    book = BookInfo(**get_book_info(target_fname))
    course = book.invpartnumber
    source_file = get_zip(course)
    return resource(source_file, target_fname)


def unsource_cli(course: str) -> FileName:
    """
    This function reorganizes the XML source files so that XTM will parse them
    in the same order as they appear in the published PDF.
    :param course: Course number to be prepped, e.g. RH124, CL310, DO180.
    :return zip_filename: Name of restructured .ZIP package that is
    ready to be uploaded to XTM for analysis.
    """
    source_file = get_zip(course)
    return unsource(source_file)


if __name__ == "__main__":
    if sys.argv[1].lower() == 'resource':
        target_file = FileName(sys.argv[2])
        resource_cli(target_file)
    if sys.argv[1].lower() == 'unsource':
        course_name = sys.argv[2]
        unsource_cli(course_name)
