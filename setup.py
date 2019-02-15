from setuptools import setup

setup(name='core',
      version='1.0',
      description='Repository with several utilities',
      url='https://github.com/sforazz/core.git',
      python_requires='>=3.5',
      author='Francesco Sforazzini',
      author_email='f.sforazzini@dkfz.de',
      license='Apache 2.0',
      zip_safe=False,
      install_requires=[
      'bz2file==0.98',
      'cycler==0.10.0',
      'kiwisolver==1.0.1',
      'matplotlib==3.0.2',
      'nibabel==2.3.3',
      'numpy==1.16.0',
      'pandas==0.24.0',
      'pydicom==1.2.2',
      'pynrrd==0.3.6',
      'pyparsing==2.3.1',
      'python-dateutil==2.7.5',
      'pytz==2018.9',
      'six==1.12.0'
      ],
      classifiers=[
          'Intended Audience :: Science/Research',
          'Programming Language :: Python',
          'Topic :: Scientific/Engineering',
          'Operating System :: Unix'
      ]
      )