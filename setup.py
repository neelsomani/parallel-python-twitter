from distutils.core import setup
setup(
    name='parallel-python-twitter',
    packages=['parallel_twitter'],
    version='0.1.0',
    license='MIT',
    description='Python Twitter client to distribute requests across API keys',
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