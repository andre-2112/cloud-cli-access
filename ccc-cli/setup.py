"""Setup script for CCC CLI"""
from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='ccc-cli',
    version='1.0.0',
    description='Cloud CLI Client - Cloud CLI Access Framework',
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'ccc=ccc.cli:main',
        ],
    },
    python_requires='>=3.8',
)
