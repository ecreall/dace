import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
CHANGES = open(os.path.join(here, 'CHANGES.md')).read()

requires = [
    'BTrees',
    'pyramid',
    'pyramid_tm',
    'pyzmq',
    'substanced',
    'zope.processlifetime',
    ]

setup(name='ecreall_dace',
      version='2.0.0.dev0',
      description='Data-centric workflow engine (maintained fork)',
      long_description=README + '\n\n' + CHANGES,
      long_description_content_type='text/markdown',
      classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.12",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        ],
      author='Amen Souissi',
      author_email='amensouissi@ecreall.com',
      maintainer='Michaël Launay (Logikascium)',
      url='https://github.com/michaellaunay/dace/',
      project_urls={
          'Source': 'https://github.com/michaellaunay/dace',
          'Tracker': 'https://github.com/michaellaunay/dace/issues',
          'Historical upstream': 'https://github.com/ecreall/dace',
      },
      keywords='process workflow bpmn pyramid substanced',
      license="AGPLv3+",
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires + ['mock'],
      test_suite="dace",
      extras_require=dict(
          # substanced's venusian scan imports its own test modules,
          # which import mock (see docs/en/worklog.md, 2026-07-13)
          test=['mock'],
      ),
      entry_points="""\
      """,
      )
