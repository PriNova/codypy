from setuptools import setup, find_packages

# Read the contents of requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="CodyAgentPy",
    version="0.1.1",
    description="A Python wrapper binding to Cody Agent through establishing a connection to the Cody-Agent server from Sourcegraph Cody using JSON-RPC protocol over a TCP/stdio connection.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="PriNova",
    author_email="info@prinova.de",
    url="https://github.com/PriNova/CodyAgentPy",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: MIT License",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.7",
)
