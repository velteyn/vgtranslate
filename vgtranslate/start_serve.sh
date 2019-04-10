#!/bin/bash
cd ..
../ENV_APP/bin/python setup.py install
cd vg_translate
../../ENV_APP/bin/python serve.py
