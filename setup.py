import setuptools
__title__ = "SWAT-EM - Specific Winding Analyse Tool for electrical machines"
__version__ = "0.6.3"
__author__ = "Martin Baun"
__license__ = "MIT License"
__copyright__ = "Copyright 2018-2021 Martin Baun"

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="swat-em",
    version=__version__,
    author=__author__,
    author_email="mar.baun@googlemail.com",
    description="Specific Winding Analysing Tool for Electrical Machines",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/martinbaun/swat-em",
    packages=setuptools.find_packages(),
    #  packages=['swat_em'],
    package_data={'swat_em': ['themes/*', 'ui/*', 'ui/icons/*',
                              'ui/bitmaps/*', 'doc', 'doc/*',
                              'template/*']},
    platforms="any",
    install_requires=['numpy', 'QtPy', 'pyqtgraph', 'xlsxwriter'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={"gui_scripts": [
    "swat-em = swat_em.main:main"]},
)
