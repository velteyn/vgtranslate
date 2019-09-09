#!/bin/bash
cd ..
../ENV_VG1/bin/python setup.py install
cd vgtranslate
../../ENV_VG1/bin/python serve.py
