from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="tobys_terminal",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    package_data={
        'tobys_terminal': [
            'shared/assets/*',
            'shared/data/*',
            'shared/exports/**/*',  # Include all files in subdirectories
            'web/static/*',
            'web/templates/*',
        ],
    },
    entry_points={
        'console_scripts': [
            'tobys-terminal=tobys_terminal.desktop.main:main',
            'tobys-web=tobys_terminal.web.app:main',
        ],
    },
    python_requires=">=3.8",
    author="Toby",
    description="Toby's Terminal - CSS Billing System",
)
