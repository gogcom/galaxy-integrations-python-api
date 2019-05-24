from setuptools import setup, find_packages

setup(
    name="galaxy.plugin.api",
    version="0.31",
    description="Galaxy python plugin API",
    author='Galaxy team',
    author_email='galaxy@gog.com',
    packages=find_packages("src"),
    package_dir={'': 'src'},
    install_requires=[
        "aiohttp==3.5.4",
        "certifi==2019.3.9"
    ]
)
