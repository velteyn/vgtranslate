import http.client as httplib
import json

import config
import imaging
from server_client import ServerClient


class CallScreenshots:
    @classmethod
    def call_screenshot(cls, image_object, source_lang=None,
                        target_lang='en', fast=None, free=None):
        return cls.call_screenshot_api(image_object, source_lang,
                                       target_lang, fast, free)

    @classmethod
    def call_screenshot_api(cls, image_object=None,
                            source_lang=None, target_lang='en',
                            fast=None, free=None):
        stored_filename = imaging.ImageSaver.save_image(image_object)
        result = ServerClient.call_server(image_object,
                                          source_lang,
                                          target_lang,
                                          fast, free)
        quota = result.get("quota", 0)
        output_image = imaging.ImageModder.write(image_object,
                                                 result, target_lang)
        imaging.ImageSaver.save_image(output_image, stored_filename)
        return output_image, quota

class CallService:
    @classmethod
    def call_service(cls, image_data, source_lang, target_lang,
                     request_output=None, mode="fast", extra=None,
                     body_kwargs=None):
        if request_output is None:
            request_output = ['image']
        request_output = ",".join(request_output)
        url = "/service?output="+request_output
        if target_lang:
            url += "&target_lang="+target_lang
        if source_lang:
            url += "&source_lang="+source_lang
        if mode:
            url += "&mode="+mode
        url += "&api_key="+config.user_api_key
        if extra:
            for key in extra:
                url += "&"+key+"="+extra[key]
        body = {"image": image_data}
        if body_kwargs:
            for key in body_kwargs:
                body[key] = body_kwargs[key]
        conn = httplib.HTTPSConnection("ztranslate.net", 443)
        conn.request("POST", url, json.dumps(body).encode('utf-8'))
        rep = conn.getresponse()
        d = rep.read().decode('utf-8')
        output = json.loads(d)

        return output
