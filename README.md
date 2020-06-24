# xmltoxtm

This package reorganizes and subsequently restores .ZIP packages of XML files that will be published with DocBook so that XTM will parse the files in the same order as the published document, making it easier to use the reference PDF when translating the content.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

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

To restructure a source package for XTM, use the following command, where ```course``` signifies the course number being prepped for translation. The command will target the latest release of the highest version number by default, but it is also possible to indicate a specific release tag following the course argument.

```
$ python3 -m docbooktoxtm unsource <course> [release]
```

For example:

```
$ python3 -m docbooktoxtm unsource BH124 SWEL8
```

When you want to restore the source package to its original format, you can call the following command, where ```target_fname``` indicates the file name of the target package generated from XTM. (NB: The target package should be generated at the locale level and not at the all-locales level.)

```
$ python3 -m docbooktoxtm resource <target_fname>
```

For example:

```
$ python3 -m docbooktoxtm resource fr-FR.zip
```

Note also that there is no option to indicate the release tag when calling the resource command. The script will extract the release information directly from the target files to make sure that it is rebuilt with the correct release.

## Authors

* **Ryan O'Rourke**

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
