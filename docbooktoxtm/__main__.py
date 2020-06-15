import sys

from github import Github

from docbooktoxtm.functions import resource, unsource, BookInfo, get_book_info_from_zip, get_zip, \
    token

if __name__ == "__main__":
    g = Github(token)
    if sys.argv[1] == 'resource':
        target_file = sys.argv[2]
        book = BookInfo(**get_book_info_from_zip(target_file))
        course = book.invpartnumber
        release = g.get_user('RedHatTraining').get_repo(course).get_latest_release()
        source_file = get_zip(release)
        resource(source_file, target_file)
    if sys.argv[1] == 'unsource':
        course = sys.argv[2]
        release = g.get_user('RedHatTraining').get_repo(course).get_latest_release()
        source_file = get_zip(release)
        unsource(source_file)
    if sys.argv[1] == 'testing':
        print(sys.argv)


