import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()

requires = [
    'BTrees',
    'pyramid',
    'pyramid_tm',
    'pyzmq',
    'rwproperty',
    'substanced',
    'tornado',
    'zope.processlifetime',
    ]

setup(name='ecreall_dace',
      version='1.0.1',
      description='Data-centric engine',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.4",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        ],
      author='Amen Souissi',
      author_email='amensouissi@ecreall.com',
      url='https://github.com/ecreall/dace/',
      keywords='process',
      license="AGPLv3+",
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="dace",
      extras_require = dict(
          test=[],
      ),
      entry_points="""\
      """,
      )

