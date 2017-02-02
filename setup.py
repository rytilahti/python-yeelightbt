from setuptools import setup

setup(
    name='python-yeelightbt',

    version='0.0.2',
    description='Python library for interfacing with yeelight bedside lamp',
    url='https://github.com/rytilahti/python-yeelightbt',

    author='Teemu Rytilahti',
    author_email='tpr@iki.fi',

    license='GPLv3',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GPLv3 License',
        'Programming Language :: Python :: 3',
    ],

    keywords='yeelight bluepy',

    packages=["yeelightbt"],

    install_requires=['bluepy', 'construct'],
    entry_points={
        'console_scripts': [
            'yeelightbt=yeelightbt.cli:cli',
        ],
    },
)
