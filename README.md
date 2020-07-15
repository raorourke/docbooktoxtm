# `docbooktoxtm`

Utility for prepping DocBook XML packages for use as XTM source files.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

## Prerequisites

Install docbooktoxtm with ```pip```.

```
$ pip install docbooktoxtm
```
or

```
$ python3 -m pip install docbooktoxtm
```
The script also requires a GitHub API token be exported as an environment variable named ```github_token```. The script will automatically pick up the token if correctly configured and will route things properly. For information on creating a personal access token, [visit GitHub's help article on the subject for more information.](https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line)

## Usage

```console
$ docbooktoxtm [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `-v, -V, --version` : Show current version
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `resource`: Restructures source file structure for more...
* `unsource`: Restores target files exported from XTM to...

## `docbooktoxtm resource`

Restructures source file structure for more efficient parsing in XTM.

**Usage**:

```console
$ docbooktoxtm resource [OPTIONS] TARGET_FNAME
```

**Options**:

* `TARGET_FNAME`: name of target .zip package  [required]
* `--help`: Show this message and exit.

## `docbooktoxtm unsource`

Restores target files exported from XTM to original source file structure.

**Usage**:

```console
$ docbooktoxtm unsource [OPTIONS] COURSE
```

**Options**:

* `COURSE`: course name or name of source .zip package  [required]
* `-r, --release-tag TEXT`: optional GitHub release tag
* `--help`: Show this message and exit.

## Authors

* **Ryan O'Rourke**

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
