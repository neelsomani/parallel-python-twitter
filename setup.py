from setuptools import setup
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='parallel-python-twitter',
    packages=['parallel_twitter'],
    version='0.2.0',
    license='MIT',
    description='Python Twitter client to distribute requests across API keys',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Neel Somani',
    author_email='neeljaysomani@gmail.com',
    url='https://github.com/neelsomani/parallel-python-twitter',
    download_url='https://github.com/neelsomani/parallel-python-twitter/releases',
    keywords=[
        'twitter',
        'twitter api',
        'python-twitter',
        'scraping',
        'twint'
    ],
    install_requires=[
        'pytest==5.0.1',
        'python-twitter==3.5'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6'
    ],
)