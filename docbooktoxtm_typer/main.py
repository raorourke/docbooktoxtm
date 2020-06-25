import sys
 
import typer
 
from docbooktoxtm_typer.functions import target_from_xtm, source_to_xtm, BookInfo, get_book_info, get_zip, FileName
 
 
app = typer.Typer()
 
 
@app.command
def resource(target_fname: FileName) -> FileName:
   """
   This function restores the XML source files to their original structure, as
   well as restores any files that had been removed from scope during prep.
   :param target_fname: Name of target .ZIP package. This file will
    be processed in current working directory.
   :return target_file: Name of target restructured .ZIP package.
   """
   book = BookInfo(**get_book_info(target_fname))
   source_file = get_zip(book.course, book.release_tag)
   resourced_fname = target_from_xtm(source_file, target_fname)
   typer.echo(f"Resourced file name: {resourced_fname}")
 

@app.command 
def unsource(course: str, release_tag: str = None) -> FileName:
   """
   This function reorganizes the XML source files so that XTM will parse them
   in the same order as they appear in the published PDF.
   :param course: Course number to be prepped, e.g. RH124, CL310, DO180.
   :param release_tag: Indicates a specific release to download. Default is
   None and will result in the most recent release of the highest version number.
   :return zip_filename: Name of restructured .ZIP package that is
   ready to be uploaded to XTM for analysis.
   """
   source_file = get_zip(course, release_tag)
   unsourced_fname = source_to_xtm(source_file)
   typer.echo(f"Unsourced file name: {unsourced_fname}")

 
if __name__ == "__main__":
   app()