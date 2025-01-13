from setuptools import setup, find_packages
from os import path

# Read the content of requirements.txt
with open('requirements.txt') as f:
    required_packages = f.read().splitlines()

setup(
    name='HygdraAgency',
    version='0.1',
    description='Bakend API for the Argentic Advanced project maker AI',
    long_description=open('README.md').read(),  # if you have a README file
    long_description_content_type='text/markdown',
    author='Bucamp Axle',
    author_email='axle.bucamp@gmail.com',
    packages=find_packages(),
    include_package_data=True,  # if you want to include other non-Python files
    install_requires=required_packages,  # This installs packages from requirements.txt
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: GNU',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',  # adjust based on your supported Python version
)
