#!/usr/bin/env python3
# update_libs.py
# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring
#
# Retrieve the versions of packages from Arch Linux's (inc. AUR) and Alpine's repositories.
# Also try to extract versions from some download sites like basic mirrors.
#
# The code in documentation comments can also be used to test the functions by
# running "python -m doctest update_libs.py -v".
#   The "str" call is only needed to make the test pass on Python, you
#   do not need to include it when using this function.

import json
import re
import urllib.error
import urllib.request as request

import toml
from natsort import natsorted


def convert_openssl_version(version):
    """Convert OpenSSL package versions to match upstream's format

    >>> convert_openssl_version('1.1.1.m')
    '1.1.1m'
    """

    return re.sub(r'(.+)\.([a-z])', r'\1\2', version)


def convert_sqlite_version(version):
    """Convert SQLite package versions to match upstream's format

    >>> convert_sqlite_version('3.37.2')
    '3370200'
    """

    matches = re.match(r'(\d+)\.(\d+)\.(\d+)', version)
    return f'{int(matches.group(1)):d}{int(matches.group(2)):02d}{int(matches.group(3)):02d}00'


def pkgver(package):
    """Retrieve the current version of the package in Arch Linux repos
    API documentation: https://wiki.archlinux.org/index.php/Official_repositories_web_interface

    >>> str(pkgver('zlib'))
    '1.2.11'
    """

    # Though the URL contains "/search/", this only returns exact matches (see API documentation)
    url = f'https://www.archlinux.org/packages/search/json/?name={package}'
    req = request.urlopen(url)
    metadata = json.loads(req.read())
    req.close()
    try:
        return metadata['results'][0]['pkgver']
    except IndexError:
        return 'Package not found'


def aurver(package):
    """Retrieve the current version of the package in AUR Arch Linux repos
    API documentation: https://wiki.archlinux.org/title/Aurweb_RPC_interface

    >>> str(aurver('mariadb-connector-c'))
    '3.2.4'
    """

    # Though the URL contains "/search/", this only returns exact matches (see API documentation)
    url = f'https://aur.archlinux.org/rpc/?v=5&type=info&arg[]={package}'
    req = request.urlopen(url)
    metadata = json.loads(req.read())
    req.close()
    try:
        return metadata['results'][0]['Version'].rsplit('-', 1)[0]
    except IndexError:
        return 'Package not found'


def alpinever(package):
    """Retrieve the current version of the package in Alpine repos

    >>> str(alpinever('mariadb-connector-c'))
    '3.1.13'
    """

    try:
        # Though the URL contains "/search/", this only returns exact matches (see API documentation)
        url = f'https://git.alpinelinux.org/aports/plain/main/{package}/APKBUILD'
        req = request.urlopen(url)
        apkbuild = req.read(1024).decode('utf-8')
        req.close()

        matches = re.search(r'pkgver=(.*)\n', apkbuild, re.MULTILINE)
        return f'{matches.group(1)}'
    except urllib.error.HTTPError:
        return 'Package not found'


def mirrorver(site, href_prefix, strip_prefix=None, re_postfix=r'[\/]?\"'):
    # pylint: disable=anomalous-backslash-in-string
    """Retrieve the current version of the package in Alpine repos

    # >>> str(mirrorver('https://ftp.nluug.nl/db/mariadb/', r'connector-c-3\.1\.', 'connector-c-'))
    # '3.1.15'
    """

    try:
        url = f'{site}'
        req = request.urlopen(url)
        site_html = req.read(10240).decode('utf-8')
        req.close()

        matches = re.findall(fr'href=\"({href_prefix}.*?){re_postfix}', site_html, re.MULTILINE)
        latest_version = natsorted(matches).pop().replace(strip_prefix, '')
        return f'{latest_version}'
    except urllib.error.HTTPError:
        return 'Package not found'


def rustup_version():
    """
    Retrieve the current version of Rustup from https://static.rust-lang.org/rustup/release-stable.toml

    :return: The current Rustup version
    """

    req = request.urlopen('https://static.rust-lang.org/rustup/release-stable.toml')
    metadata = toml.loads(req.read().decode("utf-8"))
    req.close()

    return metadata['version']


if __name__ == '__main__':
    PACKAGES = {
        'SSL': mirrorver('https://ftp.openssl.org/source/', r'openssl-1\.\d\.\d\w+', 'openssl-', r''),
        'CURL': mirrorver('https://curl.se/download/', r'download\/curl-7\.\d+\.\d+', r'download/curl-', r'\.tar\.xz'),
        'ZLIB': pkgver('zlib'),
        'PQ_11': mirrorver('https://ftp.postgresql.org/pub/source/', r'v11\.', 'v'),
        'PQ_14': mirrorver('https://ftp.postgresql.org/pub/source/', r'v14\.', 'v'),
        'SQLITE': convert_sqlite_version(pkgver('sqlite')),
        'MARIADB': mirrorver('https://ftp.nluug.nl/db/mariadb/', r'connector-c-3\.2\.', 'connector-c-'),
        '---': '---', # Also print some other version or from other resources just to compare.
        'SSL3': mirrorver('https://ftp.openssl.org/source/', r'openssl-3\.\d\.\d', 'openssl-', r''),
        'SSL_ARCH': convert_openssl_version(pkgver('openssl')),
        'CURL_ARCH': pkgver('curl'),
        'RUSTUP': rustup_version(),
        'PQ_ARCH': pkgver('postgresql'),
        'PQ_ALPINE': alpinever('postgresql14'),
        'PQ_12': mirrorver('https://ftp.postgresql.org/pub/source/', r'v12\.', 'v'),
        'PQ_13': mirrorver('https://ftp.postgresql.org/pub/source/', r'v13\.', 'v'),
        'MARIADB_ALPINE': alpinever('mariadb-connector-c'),
        'MARIADB_AUR': aurver('mariadb-connector-c'),
        'MARIADB_3_1': mirrorver('https://ftp.nluug.nl/db/mariadb/', r'connector-c-3\.1\.', 'connector-c-'),
    }

    # Show a list of packages with current versions
    # pylint: disable=consider-using-dict-items
    for prefix in PACKAGES:
        if prefix == '---':
            print(f'{prefix}')
        else:
            print(f'{prefix}_VER="{PACKAGES[prefix]}"')
