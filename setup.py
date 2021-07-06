# Copyright (C) 2021 Samuel Baker


def readme():
    with open('README.md') as f:
        return f.read()


DESCRIPTION = "Weight ESRI shapefiles attributes"
LONG_DESCRIPTION_CONTENT_TYPE = "text/markdown"

DISTNAME = 'weightGIS'
MAINTAINER = 'Samuel Baker'
MAINTAINER_EMAIL = 'samuelbaker.researcher@gmail.com'
LICENSE = 'MIT'
DOWNLOAD_URL = "https://github.com/sbaker-dev/weightGIS"
VERSION = "0.11.0"
PYTHON_REQUIRES = ">=3.6"

INSTALL_REQUIRES = [

    'csvObject', 'shapeObject', 'shapely', 'miscSupports', 'numpy']

CLASSIFIERS = [
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'License :: OSI Approved :: MIT License',
]

if __name__ == "__main__":

    from setuptools import setup, find_packages

    import sys

    if sys.version_info[:2] < (3, 7):
        raise RuntimeError("weightGIS requires python >= 3.7.")

    setup(
        name=DISTNAME,
        author=MAINTAINER,
        author_email=MAINTAINER_EMAIL,
        maintainer=MAINTAINER,
        maintainer_email=MAINTAINER_EMAIL,
        description=DESCRIPTION,
        long_description=readme(),
        long_description_content_type=LONG_DESCRIPTION_CONTENT_TYPE,
        license=LICENSE,
        version=VERSION,
        download_url=DOWNLOAD_URL,
        python_requires=PYTHON_REQUIRES,
        install_requires=INSTALL_REQUIRES,
        packages=find_packages(),
        classifiers=CLASSIFIERS
    )
