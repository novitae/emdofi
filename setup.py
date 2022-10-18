from setuptools import setup, find_packages

setup(
    name = 'emdofi',
    version = '1.0.0',
    author = 'novitae',
    url = 'https://github.com/novitae/emdofi',
    license = 'GNU General Public License v3 (GPLv3)',
    classifiers = [
        'Programming Language :: Python :: 3.10',
    ],
    packages = find_packages(),
    package_data = {"": ["./domains/all_email_provider_domains.txt"]},
    include_package_data = True,
    install_requires = ['argparse'],
    entry_points = {'console_scripts': ['emdofi = emdofi.__main__:main']}
)