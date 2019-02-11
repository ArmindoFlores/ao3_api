import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ao3-api",
    version="0.0.1",
    author="Francisco Rodrigues",
    author_email="francisco.rodrigues0908@gmail.com",
    description="An unofficial AO3 (archiveofourown.org) API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
