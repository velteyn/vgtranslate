# VGTranslate

Lightweight server for doing OCR and machine translation on game screen captures.  Suitable as an endpoint for real time usage, and can act as an open-source alternative to the ztranslate client.  Uses python 2.7.  Licensed under GNU GPLv3.

INSTALLATION:
    1.) Download this repo and extract it.  If you have git you can do: `git clone https://gitlab.com/spherebeaker/vgtranslate.git` instead.
    2.) Copy `default_config.json` to `config.json` (in the vgtranslate folder) and modify the configuration to point to the OCR/MT apis you want to use (see EXAMPLES below).
    3.) Install python (v2.7) to your system.
    4.) Run `python setup.py install` in the base folder to install the required packages (in a virtualenv).
    5.) Run `python serve.py` in the vgtranslate directory.

EXAMPLE configurations for config.json:

### use ztranslate.net
```
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
```


### use google ocr and translation
```
{
    "default_target": "En",
    "local_server_api_key_type": "google",
    "local_server_ocr_key": "google cloud vison api key",
    "local_server_host": "localhost",
    "local_server_port": 4404,
    "local_server_translation_key": "google cloud translation api key",
    "local_server_enabled": true
}
```

### use tesseract locally, and then google translate:
```
{
    "default_target": "En",
    "local_server_api_key_type": "tess_google",
    "local_server_host": "localhost",
    "local_server_ocr_processor": {
      "source_lang": "jpn",
      "pipeline": [
        {"action": "reduceToMultiColor",
         "options": {
           "base": "000000",
           "colors": [
             ["FFFFFF", "FFFFFF"]
           ],
           "threshold": 32
         }
        }
      ]
    },
    "local_server_port": 4404,
    "local_server_translation_key": "google cloud translation api key",
    "local_server_enabled": true
}
```


