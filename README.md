# VGTranslate

Lightweight server for doing OCR and machine translation on game screen captures.  Suitable as an endpoint for real time usage, and can act as an open-source alternative to the ztranslate client.  Licensed under GNU GPLv3.

USAGE:
    copy default_config.json to config.json and modify the configuration to point to the OCR/MT apis you want to use.  Run python setup.py install to install the required packages (preferably in a virtualenv), and then run serve.py in the vgtranslate directory.

EXAMPLE configurations for config.json:

### use ztranslate.net
{
    "server_host": "ztranslate.net",
    "server_port": 443,
    "default_target": "En",
    "local_server_api_key_type": "ztranslate",
    "local_server_host": "localhost",
    "local_server_port": 4404,
    "user_api_key": "<ztranslate.net api key>",
    "local_server_enabled": true
}

### use google ocr and translation
{
    "default_target": "En",
    "local_server_api_key_type": "google",
    "local_server_ocr_key": "google cloud vison api key",
    "local_server_host": "localhost",
    "local_server_port": 4404,
    "local_server_translation_key": "google cloud translation api key",
    "local_server_enabled": true
}

