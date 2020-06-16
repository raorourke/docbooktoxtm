# xmltoxtm

This package reorganizes and subsequently restores .ZIP packages of XML files that will be published with DocBook so that XTM will parse the files in the same order as the published document, making it easier to use the reference PDF when translating the content.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

Install xmltoxtm with ```pip```.

```
$ pip install xmltoxtm
```
or

```
$ python3 -m pip install xmltoxtm
```

## Usage

To restructure a source package for XTM, use the following command, where ```course``` signifies the course number being prepped for translation. The command will target the latest release of the highest version number by default, but it is also possible to indicate a specific release tag following the course argument.

```
$ python3 -m xmltoxtm unsource <course> [release]
```

For example:

```
$ python3 -m xmltoxtm unsource BH124 SWEL8
```

When you want to restore the source package to its original format, you can call the following command, where ```target_fname``` indicates the file name of the target package generated from XTM. (NB: The target package should be generated at the locale level and not at the all-locales level.)

```
$ python3 -m xmltoxtm resource <target_fname>
```

For example:

```
$ python3 -m xmltoxtm resource fr-FR.zip
```

Note also that there is no option to indicate the release tag when calling the resource command. The script will extract the release information directly from the target files to make sure that it is rebuilt with the correct release.

## Authors

* **Ryan O'Rourke**

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
