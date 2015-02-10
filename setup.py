from setuptools import setup, find_packages
import os
import glob

package_dir = {'': 'src'}
for pkg in [pkg for pkg in find_packages("src") if pkg.find('.') > -1]:
    package_dir['rocketblast' + "." + pkg] = "src" + os.sep + pkg

datadir = os.path.join('data')
data_files = [(datadir, [f for f in glob.glob(os.path.join(datadir, '*'))])]

setup(
    name='Rocket Blast RCON Troller',
    version='0.1.1',
    # maintainer       = '',
    #    maintainer_email = '',
    author='Martin Danielson',
    author_email='martin@rocketblast.com',
    long_description=open("README.md").read(),
    keywords='rcon battlefield game servers mods plugin socket connection',
    description='Plugin system to write game servers modifications (Battlefield)',
    license='GNU Affero GPL v3',
    #    platforms        = '',
    url='https://github.com/rocketblast/rcon-troller',
    download_url='https://github.com/rocketblast/rcon-troller/downloads',
    classifiers='',

    # package installation
    package_dir=package_dir,
    packages=find_packages('src'),
    namespace_packages=['rocketblast', 'rocketblast.rcon'],

    install_requires=['pygeoip', 'rocket_blast_rcon'],
    dependency_links=['https://github.com/rocketblast/rcon/archive/master.zip#egg=rocket_blast_rcon'],
    # uncomment if you have share/data files
    data_files=data_files,

    #use_2to3 = True, # causes issue with nosetests
)