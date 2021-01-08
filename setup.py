###############################################################################
# (C) Copyright 2020 Andrea Sorbini
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as 
# published by the Free Software Foundation, either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
###############################################################################
import setuptools

with open("README.md", "r") as readme_f:
    readme_contents = readme_f.read()

setuptools.setup(
    name="yaml-serde",
    version="0.2.1",
    author="Andrea Sorbini",
    author_email="as@mentalsmash.org",
    description="Python library for simplified YAML object serialization",
    license="License :: OSI Approved :: Apache Software License",
    long_description=readme_contents,
    long_description_content_type="text/markdown",
    url="https://github.com/asorbini/yaml-serde",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
    ],
    python_requires='>=3.6, <4',
    install_requires=[
        "pyyaml>=5.1",
    ],
)
