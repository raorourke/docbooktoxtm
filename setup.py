import pathlib
from setuptools import setup, find_packages

HERE = pathlib.Path(__file__).parent

VERSION = '1.0.dev1'
PACKAGE_NAME = 'docbooktoxtm'
AUTHOR = 'Ryan O\'Rourke'
AUTHOR_EMAIL = 'ryan.orourke@welocalize.com'
URL = 'https://github.com/raorourke/docbooktoxtm'

LICENSE = 'MIT License'
DESCRIPTION = 'Disassemble and reassemble source package structure for better use as XTM source file.'
LONG_DESCRIPTION = (HERE / "README.md").read_text()
LONG_DESC_TYPE = "text/markdown"

INSTALL_REQUIRES = [
      'xmltodict',
      'lxml',
      'pydantic',
      'PyGithub',
      'requests'
]

setup(name=PACKAGE_NAME,
      version=VERSION,
      python_requires='>3.8',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      long_description_content_type=LONG_DESC_TYPE,
      author=AUTHOR,
      license=LICENSE,
      author_email=AUTHOR_EMAIL,
      url=URL,
      install_requires=INSTALL_REQUIRES,
      packages=find_packages()
      )
