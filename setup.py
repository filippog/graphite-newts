from setuptools import find_packages, setup

setup(
    name                 ='graphite-newts',
    version              = '0.1',
    packages             = find_packages(),
    description          = 'A graphite storage finder for Newts.',
    author               = 'Filippo Giunchedi',
    author_email         = 'fgiunchedi@wikimedia.org',
    install_requires     = ['graphite-api', 'requests', 'click', 'parsedatetime'],
    include_package_data = True,
    setup_requires       = ['nose>=1.0'],
    tests_require        = ['requests-mock', 'coverage'],
    entry_points         = {'console_scripts':
                               ['graphite-newts=graphite_newts.cli:main']
                           },
    classifiers          = [
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
)
