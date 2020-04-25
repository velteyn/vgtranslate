#!/bin/bash
cd ..
../ENV_APP/bin/python setup.py install
cd vgtranslate
../../ENV_APP/bin/python app.py
