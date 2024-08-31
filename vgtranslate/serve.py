#!/usr/bin/env python3

import base64
import functools
import html
import http.client as httplib
import http.server
import json
import os
import re
import sys
import threading
import time
import urllib.parse

from PIL import Image, ImageDraw, ImageEnhance

import config
import imaging
import ocr_tools
import screen_translate
from text_to_speech import TextToSpeech
from util import (color_hex_to_byte, fix_neg_width_height, image_to_string,
                  image_to_string_format, load_image, reduce_to_multi_color,
                  reduce_to_text_color, segfill, swap_red_blue)

# Dictionary going from ISO-639-1 to ISO-639-2/T language codes (mostly):
lang_2_to_3 = {
    "ja": "jpn",
    "de": "deu",
    "en": "eng",
    "es": "spa",
    "fr": "fra",
    "zh": "zho",
    "zh-CN": "zho",  # BCP-47
    "zh-TW": "zho",  # BCP-47
    "nl": "nld",
    "it": "ita",
    "pt": "por",
    "ru": "rus"
}

USE_ESPEAK = False

server_thread = None
httpd_server = None
window_obj = None

g_debug_mode = 0

SOUND_FORMATS = {"wav": 1}
IMAGE_FORMATS = {"bmp": 1, "png": 1}


class ServerOCR:
    @classmethod
    def _preprocess_color(cls, image_data, colors="FFFFFF"):
        img = load_image(image_data)
        bg = "000000"
        if colors.lower().strip() == "detect":
            pass
        elif colors:
            print("Pre process ", colors)
            try:
                colors = [x.strip() for x in re.split(",| |;", colors)]
                new_colors = list()
                for color in colors:
                    if not color:
                        continue
                    if color[:2].lower() == "bg":
                        bg = color[2:8]
                    else:
                        c = color[:6]
                        if len(color) > 6:
                            try:
                                num = int(color[6:])
                            except:
                                num = 32
                        else:
                            num = 32
                        new_colors.append([color, num])
                img = reduce_to_text_color(img, new_colors, bg)
                print("succ=true")
            except:
                raise
        return bg, image_to_string(img.convert("RGBA"))

    @classmethod
    def _preprocess_image(cls, image_data, contrast=2.0):
        img = load_image(image_data)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast)
        return image_to_string(img)

    @classmethod
    def _preprocess_box(cls, image_data, box, bg):
        try:
            box2 = [int(x) for x in box.split(",")]
            box = {"x1": box2[0], "y1": box2[1], "x2": box2[2], "y2": box2[3]}
        except:
            return image_data

        img = load_image(image_data).convert("RGB")
        draw = ImageDraw.Draw(img)
        bg = color_hex_to_byte(bg)
        fill_color = bg

        recs = [[0, 0, img.width, box['y1'] - 1],
                [0, box['y2'], img.width, img.height],
                [0, 0, box['x1'] - 1, img.height],
                [box['x2'], 0, img.width, img.height]]

        for rec in recs:
            if rec[0] < 0:
                rec[0] = 0
            if rec[0] > img.width:
                rec[0] = img.width
            if rec[1] < 0:
                rec[1] = 0
            if rec[1] > img.height:
                rec[1] = img.height

            if rec[2] < 0:
                rec[2] = 0
            if rec[2] > img.width:
                rec[2] = img.width
            if rec[3] < 0:
                rec[3] = 0
            if rec[3] > img.height:
                rec[3] = img.height
            draw.rectangle(rec, fill=fill_color)
        return image_to_string(img)


class APIHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><head><title></title></head><body>yo!</body></html>")
        except ConnectionAbortedError as e:
            print(f"ConnectionAbortedError: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def do_POST(self):
        print("____")
        query = urllib.parse.urlparse(self.path).query
        if query.strip():
            query_components = dict(qc.split("=") for qc in query.split("&"))
        else:
            query_components = {}
        content_length = int(self.headers.get('Content-Length', 0))
        data = self.rfile.read(content_length)
        print(data[:100])
        print(content_length)
        print(data[-100:])
        data = json.loads(data)

        start_time = time.time()

        result = self._process_request(data, query_components)
        print("AUTO AUTO")
        print(['Request took: ', time.time() - start_time])
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        output = json.dumps(result)
        print(['out:', output[-100:]])
        self.send_header("Content-Length", len(output))
        self.end_headers()

        print("Output length: " + str(len(output)))
        self.wfile.write(output.encode())

    def _process_request(self, body, query):
        source_lang = query.get("source_lang")
        target_lang = query.get("target_lang", "en")
        mode = query.get("mode", "fast")
        request_output = query.get("output", "image,sound").lower()
        request_output = request_output.split(",")

        request_out_dict = dict()
        alpha = False
        error_string = ""

        for entry in request_output:
            if entry == 'image' and 'image' not in request_out_dict:
                request_out_dict['image'] = 'bmp'
            elif entry == 'sound' and 'sound' not in request_out_dict:
                request_out_dict['sound'] = 'wav'
            else:
                if SOUND_FORMATS.get(entry):
                    request_out_dict['sound'] = entry
                else:
                    if entry[-2:] == "-a":
                        request_out_dict['image'] = entry[:-2]
                        alpha = True
                    else:
                        request_out_dict['image'] = entry

        print(request_output)
        pixel_format = "RGB"
        image_data = body.get("image")

        image_object = load_image(image_data).convert("RGB")
        print("w: " + str(image_object.width) + " h: " + str(image_object.height))
        if pixel_format == "BGR":
            image_object = image_object.convert("RGB")
            image_object = swap_red_blue(image_object)

        result = {}
        if window_obj and config.local_server_api_key_type == "free":
            # TODO
            pass
        elif config.local_server_api_key_type == "ztranslate":
            image_object = load_image(image_data)

            if "image" not in request_out_dict and mode != "normal":
                image_object = image_object.convert("LA").convert("RGB")
                image_object = image_object.convert("P", palette=Image.ADAPTIVE, colors=32)
            else:
                image_object = image_object.convert("P", palette=Image.ADAPTIVE)

            # Pass the call onto the ztranslate service api...

            body_kwargs = dict()
            for key in body:
                if key != "image":
                    body_kwargs[key] = body[key]

            image_data = image_to_string(image_object)
            output = screen_translate.CallService.call_service(image_data,
                                                               source_lang, target_lang,
                                                               mode=mode,
                                                               request_output=request_output, body_kwargs=body_kwargs)
            return output
        elif config.local_server_api_key_type == "google":
            print("using google......")
            if "image" not in request_out_dict:
                image_object = load_image(image_data).convert("LA").convert("RGB")
                image_object = image_object.convert("P", palette=Image.ADAPTIVE, colors=32)
            else:
                image_object = load_image(image_data).convert("P", palette=Image.ADAPTIVE)

            image_data = image_to_string(image_object)
            confidence = config.ocr_confidence
            if confidence is None:
                confidence = 0.6
            bg = "000000"
            if config.ocr_color:
                bg, image_data = ServerOCR._preprocess_color(image_data, config.ocr_color)
            if config.ocr_contrast and abs(config.ocr_contrast - 1.0) > 0.0001:
                image_data = ServerOCR._preprocess_image(image_data, config.ocr_contrast)
            if config.ocr_box:
                image_data = ServerOCR._preprocess_box(image_data, config.ocr_box, bg)

            print(len(image_data))

            google_api_key = config.google_translate_api_key
            if google_api_key:
                output = screen_translate.CallService.call_google_service(image_data,
                                                                          source_lang, target_lang,
                                                                          google_api_key,
                                                                          confidence,
                                                                          request_output,
                                                                          config.google_server_timeout)
                return output
        elif config.local_server_api_key_type == "free":
            # The "free" service is expected to be local to the machine.
            output = screen_translate.CallService.call_free_service(image_data,
                                                                    source_lang, target_lang,
                                                                    config.google_translate_api_key,
                                                                    mode=mode,
                                                                    request_output=request_output)
            return output

        else:
            output = screen_translate.CallService.call_service(image_data,
                                                               source_lang, target_lang,
                                                               mode=mode,
                                                               request_output=request_output)
            return output

        return result


class StoppableHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def serve_forever(self, poll_interval=0.5):
        while not self._stop_event.is_set():
            self.handle_request()

    def stop(self):
        self._stop_event.set()
        self.server_close()


def start_server():
    global server_thread, httpd_server
    server_address = ('', config.server_port)
    httpd_server = StoppableHTTPServer(server_address, APIHandler)
    server_thread = threading.Thread(target=httpd_server.serve_forever)
    server_thread.daemon = True
    server_thread.start()


def stop_server():
    global httpd_server
    if httpd_server:
        httpd_server.stop()
        httpd_server = None


if __name__ == "__main__":
    if "stop" in sys.argv:
        stop_server()
    else:
        config.load_init()
        start_server()
        print("Server is running... Press Ctrl+C to stop.")
        try:
            server_thread.join()
        except KeyboardInterrupt:
            stop_server()
