from setuptools import find_packages, setup

setup(
    name="esstat",
    version="0.0.9",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["rich", "requests", "click", "aiohttp"],
    entry_points={"console_scripts": ["esstat = esstat.main:main"]},
)
