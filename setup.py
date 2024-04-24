from setuptools import find_packages, setup

# Read the contents of requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="codypy",
    version="0.1.1",
    description="A Python wrapper binding to Cody Agent through establishing a connection to the Cody-Agent server from Sourcegraph Cody using JSON-RPC protocol over a TCP/stdio connection.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="PriNova",
    author_email="info@prinova.de",
    url="https://github.com/PriNova/codypy",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'codypy-cli = cli:main',
        ],
    },
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: MIT License",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.7",
)
