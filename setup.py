# Copyright (C) 2020 Samuel Baker

DESCRIPTION = "Weight ESRI shapefiles attributes"
LONG_DESCRIPTION = """
# weightGIS

shapefileWeights purpose is to allow you to simply create a cross relationship weight in both area and sub unit 
population (where available). All the source code is available from [the github page][repo] along with a full tutorial 
on how to use the module via a jupyter notebook alongside some example data.

[repo]: https://github.com/sbaker-dev/weightGIS

"""
LONG_DESCRIPTION_CONTENT_TYPE = "text/markdown"

DISTNAME = 'weightGIS'
MAINTAINER = 'Samuel Baker'
MAINTAINER_EMAIL = 'samuelbaker.researcher@gmail.com'
LICENSE = 'MIT'
DOWNLOAD_URL = "https://github.com/sbaker-dev/weightGIS"
VERSION = "0.10.3"
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
        long_description=LONG_DESCRIPTION,
        long_description_content_type=LONG_DESCRIPTION_CONTENT_TYPE,
        license=LICENSE,
        version=VERSION,
        download_url=DOWNLOAD_URL,
        python_requires=PYTHON_REQUIRES,
        install_requires=INSTALL_REQUIRES,
        packages=find_packages(),
        classifiers=CLASSIFIERS
    )
