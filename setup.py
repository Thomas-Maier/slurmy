import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="slurmy",
    version="1.3.1",
    author="Thomas Maier",
    author_email="thomas.maier1989@gmail.com",
    description="Manager of batch jobs accross different backends.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Thomas-Maier/slurmy",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
    ],
    scripts = ['bin/slurmy', 'bin/slurmy2'],
    install_requires=['tqdm'],
)
