from setuptools import setup, find_packages

setup(
    name="galaxy.plugin.api",
    version="0.26",
    description="Galaxy python plugin API",
    author='Galaxy team',
    author_email='galaxy@gog.com',
    packages=find_packages("src"),
    package_dir={'': 'src'}
)
