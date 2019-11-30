# VGTranslate

Lightweight server for doing OCR and machine translation on game screen captures.  Suitable as an endpoint for real time usage, and can act as an open-source alternative to the ztranslate client.  Uses python 2.7.  Licensed under GNU GPLv3.

# Installation

1. Download this repo and extract it.  If you have git you can do: `git clone https://gitlab.com/spherebeaker/vgtranslate.git` instead.
2. Copy `default_config.json` to `config.json` (in the vgtranslate folder) and modify the configuration to point to the OCR/MT apis you want to use (see the Examples section below).
3. Install python (v2.7) to your system.
4. Run `python setup.py install` in the base folder to install the required packages (in a virtualenv).
5. Run `python serve.py` in the vgtranslate directory.

If you have trouble running the above code on windows, you can try running a pre-built release:

1. Download a release here: [vgtranslate_server_v1.05.zip](https://ztranslate.net/download/vgtranslate_serve_v1.05.zip?owner=)
2. Change the `config.json` as in following section.
3. Run `serve.exe`.

If you run into trouble, you can join the RetroArch discord or the ZTranslate discord ( https://ztranslate.net/community ) and ask @Beaker for help.


# Example configurations for config.json:

You can use either use Google API keys yourself to run vgtranslate, or use an account with the ztranslate.net service.  The ZTranslate service in this case basically acts like a standalone vgtranslate server that's setup with it's own Google API keys.  The main purpose being that you can try out vgtranslate without having to sign up to Google Cloud first, and getting some savings with a volume discount on the Google Cloud api calls.  To get an API key for ZTranslate, go to https://ztranslate.net , sign up, and go to the Settings page.  The ZTranslate API key will be at the bottom.

As of writing, ztranslate.net allows 10,000 calls per month (for free), while if you sign up for Google Cloud, you get $300 worth of API credits.  Each vgtranslate call costs about 0.2-0.3 cents, so it makes sense to use the Google API keys directly instead of pooling than with ZTranslate, at least at first.

See: https://cloud.google.com/billing/docs/how-to/manage-billing-account about how to create a Google Cloud account and https://cloud.google.com/docs/authentication/api-keys about creating Google Cloud API keys

If using Google Cloud keys, be sure to set the API key to not have restricted APIs at all, or at least include the Cloud Vision API, Cloud Translation API, and Cloud Text-to-Speech API in the list of allowed APIs. 

### Using ztranslate.net
```
{
    "server_host": "ztranslate.net",
    "server_port": 443,
    "default_target": "En",
    "local_server_api_key_type": "ztranslate",
    "local_server_host": "localhost",
    "local_server_port": 4404,
    "user_api_key": "ztranslate.net api key goes here",
    "local_server_enabled": true
}
```

### Using Google OCR and translation
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

### Using tesseract locally, and then Google translate (experimental):
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


