from setuptools import setup, find_packages
from lega import __version__

setup(name='lega',
      version=__version__,
      url='https://neic-sda.readthedocs.io/',
      license='Apache License 2.0',
      author='NeIC System Developers',
      description='SDA',
      long_description='''\
LocalEGA ingests into its archive, files that are dropped in some inbox.

The program is divided into several components interconnected via a
message broker and a database.

Users are handled through Central EGA, directly.
''',
      packages=find_packages(),
      include_package_data=False,
      package_data={'lega': ['conf/loggers/*.yaml', 'conf/defaults.ini']},
      zip_safe=False,
      entry_points={
          'console_scripts': [
              'ega-ingest = lega.ingest:main',
              'ega-verify = lega.verify:main',
              'ega-finalize = lega.finalize:main',
              'ega-conf = lega.conf.__main__:main',
          ]
      },
      platforms='any',
      install_requires=[
          'pika',
          'aiohttp',
          'psycopg2>=2.8.4',
          'PyYaml',
          'boto3>=1.13.10',
          'requests',
          'crypt4gh @ git+https://github.com/EGA-archive/crypt4gh.git@v1.1',
          'tox'
      ],
      extras_require={
          'test': ['pytest',
                   'pytest-cov',
                   'aioresponses',
                   'testfixtures',
                   'coveralls', 'coverage==4.5.4'],
          'docs': [
              'sphinx >= 1.4',
              'sphinx_rtd_theme', 'recommonmark']}
      )
