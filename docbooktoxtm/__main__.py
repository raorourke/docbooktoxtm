import sys

from github import Github

from docbooktoxtm.functions import resource, unsource, BookInfo, get_book_info_from_zip, get_zip, \
    token


def resource_cli(target_file: str) -> str:
    """
    This function restores the XML source files to their original structure, as
    well as restores any files that had been removed from scope during prep.
    :param target_file: Name of target .ZIP file. Will be processed in current working directory.
    :return target_file: Name of target restructured .ZIP file.
    """
    book = BookInfo(**get_book_info_from_zip(target_file))
    course = book.invpartnumber
    release = g.get_user('RedHatTraining').get_repo(course).get_latest_release()
    source_file = get_zip(release)
    return resource(source_file, target_file)


def unsource_cli(course: str) -> str:
    """
    This function reorganizes the XML source files so that XTM will parse them
    in the same order as they appear in the published PDF.
    :param course: Course number to be prepped, e.g. RH124, CL310, DO180.
    :return zip_filename: Name of restructured .ZIP file ready to be uploaded to XTM for analysis.
    """
    release = g.get_user('RedHatTraining').get_repo(course).get_latest_release()
    source_file = get_zip(release)
    return unsource(source_file)


if __name__ == "__main__":
    g = Github(token)
    if sys.argv[1].lower() == 'resource':
        target_file = sys.argv[2]
        resource_cli(target_file)
    if sys.argv[1].lower() == 'unsource':
        course = sys.argv[2]
        unsource_cli(course)


