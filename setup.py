import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ao3-api",
    version="2.0.3",
    author="Francisco Rodrigues",
    author_email="francisco.rodrigues0908@gmail.com",
    description="An unofficial AO3 (archiveofourown.org) API",
    python_requires='>=3.8',
    install_requires=[
        "BeautifulSoup4",
        "requests",
        "lxml"
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ArmindoFlores/ao3_api",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
