import sys

from xmltoxtm.functions import resource, unsource, BookInfo, get_book_info_from_zip, get_zip


def resource_cli(target_file: str) -> str:
    """
    This function restores the XML source files to their original structure, as
    well as restores any files that had been removed from scope during prep.
    :param target_file: Name of target .ZIP package. Will be processed in current working directory.
    :return target_file: Name of target restructured .ZIP package.
    """
    book = BookInfo(**get_book_info_from_zip(target_file))
    course = book.invpartnumber
    source_file = get_zip(course)
    return resource(source_file, target_file)


def unsource_cli(course: str) -> str:
    """
    This function reorganizes the XML source files so that XTM will parse them
    in the same order as they appear in the published PDF.
    :param course: Course number to be prepped, e.g. RH124, CL310, DO180.
    :return zip_filename: Name of restructured .ZIP package ready to be uploaded to XTM for analysis.
    """
    source_file = get_zip(course)
    return unsource(source_file)


if __name__ == "__main__":
    if sys.argv[1].lower() == 'resource':
        target_file = sys.argv[2]
        resource_cli(target_file)
    if sys.argv[1].lower() == 'unsource':
        course = sys.argv[2]
        unsource_cli(course)
