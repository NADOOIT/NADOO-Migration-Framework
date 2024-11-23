from setuptools import setup, find_packages

setup(
    name="nadoo_migration_framework",
    version="0.3.3",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "libcst>=0.4.0",
        "toml>=0.10.2",
        "pytest>=7.0.0",
        "typing-extensions>=4.0.0",
    ],
    python_requires=">=3.8",
)
