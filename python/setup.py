# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['pi_trading_lib', 'pi_trading_lib.data']

package_data = \
{'': ['*']}

install_requires = \
['pandas>=1,<2', 'python-dateutil>=2.8.1,<3.0.0']

setup_kwargs = {
    'name': 'pi-trading-lib',
    'version': '0.1.0',
    'description': '',
    'long_description': None,
    'author': 'David Zeng',
    'author_email': 'davidzeng.42@gmail.com',
    'maintainer': None,
    'maintainer_email': None,
    'url': None,
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'python_requires': '>=3.8,<4.0',
}


setup(**setup_kwargs)
