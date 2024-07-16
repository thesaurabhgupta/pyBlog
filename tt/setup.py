from setuptools import setup, find_packages

setup(
    name='c3papplication',    
    packages= find_packages(),
    version='0.1',
    description='C3P Python project apis',
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'c3papp=c3prun:main'
        ]
    },
    install_requires=[
        "APScheduler==3.7.0",
        "arrow==0.17.0",
        "Authlib==0.14.3",
        "bcrypt==3.2.0",
        "cachetools==4.2.0",
        "certifi==2020.12.5",
        "cffi==1.14.4",
        "chardet==4.0.0",
        "cliapp==1.0.9",
        "click==7.1.2",
        "cmdtest==0.1.1",
        "cryptography==3.3.1",
        "defer==1.0.4",
        "Flask==1.1.2",
        "Flask-API==2.0",
        "Flask-Cors==3.0.9",
        "Flask-HTTPAuth==4.2.0",
        "Flask-SQLAlchemy==2.5.1",
        "future==0.18.2",
        "google-api-core==1.24.1",
        "google-api-python-client==1.12.8",
        "google-auth==1.24.0",
        "google-auth-httplib2==0.0.4",
        "google-auth-oauthlib==0.4.2",
        "google-cloud-core==1.5.0",
        "google-cloud-storage==1.35.0",
        "google-crc32c==1.1.0",
        "google-oauth==1.0.1",
        "google-resumable-media==1.2.0",
        "googleapis-common-protos==1.52.0",
        "gunicorn==20.0.4",
        "httplib2==0.18.1",
        "icmplib==2.0",
        "idna==2.10",
        "itsdangerous==1.1.0",
        "Jinja2==2.11.2",
        "jproperties==2.1.0",
        "louis==1.3",
        "lxml==4.6.2",
        "MarkupSafe==1.1.1",
        "mysql-connector-python==8.0.22",
        "ncclient==0.6.9",
        "netmiko==3.4.0",
        "ntc-templates==2.3.1",
        "numpy==1.19.4",
        "oauthlib==3.0.0",
        "pandas==1.1.3",
        "paramiko==2.7.2",
        "pdfkit==0.6.1",
        "ply==3.11",
        "protobuf==3.14.0",
        "pyasn1==0.4.8",
        "pyasn1-modules==0.2.8",
        "pycparser==2.20",
        "pycryptodomex==3.9.9",
        "pymongo==3.11.3",
        "PyNaCl==1.4.0",
        "pyOpenSSL==20.0.1",
        "pysmi==0.3.4",
        "pysnmp==4.4.12",
        "python-dateutil==2.8.1",
        "python-debian==0.1.39",
        "pythonping==1.0.15",
        "pytz==2020.5",
        "requests==2.25.1",
        "requests-oauthlib==1.2.0",
        "rsa==4.6",
        "scp==0.13.6",
        "six==1.15.0",
        "SQLAlchemy==1.4.15",
        "tenacity==8.0.1",
        "textfsm==1.1.2",
        "times==0.7",
        "tzlocal==2.1",
        "uritemplate==3.0.1",
        "uritemplate.py==3.0.2",
        "urllib3==1.26.2",
        "Werkzeug==1.0.1",
        "xlrd==2.0.1",
        "xlwt==1.3.0",
        
    ],
)