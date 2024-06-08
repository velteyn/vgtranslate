import base64
import http.client as http
import io
import json
import time

import config
from PIL import Image


class ServerClient:
    @staticmethod
    def call_server(image_object, source_lang, target_lang, fast, free):
        if fast:
            mode = "fast"
        elif free:
            mode = "free"
        else:
            mode = "normal"

        if mode == "fast":
            # Speeds up upload by 4x, but inexact pixels
            image_object = image_object.convert("P", palette=Image.ADAPTIVE)

        image_byte_array = io.BytesIO()
        image_object.save(image_byte_array, format='PNG')
        image_data = image_byte_array.getvalue()

        image_data = base64.b64encode(image_data)

        body = {
            "timestamp": "",
            "api_key": config.user_api_key,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "image": image_data.decode('utf-8'),  # Decoding to str
            "mode": mode
        }
        t_time = time.time()

        try:
            conn = http.HTTPSConnection(config.server_host, config.server_port)
            conn.request("POST", "/ocr", json.dumps(body).encode('utf-8'))  # Encoding to bytes
            rep = conn.getresponse()
            d = rep.read().decode('utf-8')  # Decoding response
            output = json.loads(d)
            print(['Took: ', time.time()-t_time])

            return output
        except Exception as e:
            import traceback
            traceback.print_exc()
            print([body])
            print("===")
            print([d])
            raise

    @staticmethod
    def get_quota():
        body = {
            "api_key": config.user_api_key,
        }
        try:
            conn = http.HTTPSConnection(config.server_host, config.server_port)
            conn.request("POST", "/quota", json.dumps(body).encode('utf-8'))  # Encoding to bytes
            rep = conn.getresponse()
            d = rep.read().decode('utf-8')  # Decoding response
            output = json.loads(d)
            return output
        except Exception as e:
            return dict()
