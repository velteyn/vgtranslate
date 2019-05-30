import BaseHTTPServer
import HTMLParser
import time
import json
import config
import threading
import httplib
import functools
import urlparse
import os
import base64
from util import load_image, image_to_string, fix_neg_width_height,\
                 image_to_string_bmp, swap_red_blue, segfill,\
                 reduce_to_multi_color
import screen_translate
import imaging
import ocr_tools
from text_to_speech import TextToSpeech
import sys
from PIL import Image

#dictionary going from ISO-639-1 to ISO-639-2/T language codes (mostly):
lang_2_to_3 = {
  "ja": "jpn",
  "de": "deu", 
  "en": "eng",
  "es": "spa",
  "fr": "fra",
  "zh": "zho",
  "zh-CN": "zho",#BCP-47
  "zh-TW": "zho",#BCP-47
  "nl": "nld",
  "it": "ita",
  "pt": "por",
  "ru": "rus"
}

USE_ESPEAK = False

server_thread = None
httpd_server = None
window_obj =  None

g_debug_mode = 0

class APIHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("<html><head><title></title></head></html>")
        self.wfile.write("<body>yo!</body></html>")
        
    def do_POST(self):
        query = urlparse.urlparse(self.path).query
        if query.strip():
            query_components = dict(qc.split("=") for qc in query.split("&"))
        else:
            query_components = {}
        content_length = int(self.headers.getheader('content-length', 0))
        data = self.rfile.read(content_length);
        print content_length
        data = json.loads(data)
        
        start_time = time.time()

        result = self._process_request(data, query_components)
        print ['Request took: ', time.time()-start_time]
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        output = json.dumps(result)
        self.send_header("Content-Length", len(output))
        self.end_headers()

        print "Output length: "+str(len(output))
        self.wfile.write(output)

    def _process_request(self, body, query):
        source_lang = query.get("source_lang")
        target_lang = query.get("target_lang", "en")
        request_output = query.get("output", "image,sound")
        request_output = request_output.split(",")
        print request_output
        #pixel_format = body.get("pixel_format", "RGB")

        pixel_format = "RGB"
        image_data = body.get("image")
        
        image_object = load_image(image_data).convert("RGB")
        if pixel_format == "BGR": 
            image_object = image_object.convert("RGB")
            image_object = swap_red_blue(image_object)
        
        result = {}
        if window_obj and config.local_server_api_key_type == "free":
            #TODO
            pass
        elif config.local_server_api_key_type == "ztranslate":
            image_object = load_image(image_data)

            if window_obj and window_obj.top_ui_mode.get() == "Fast":
                fast = True
            else:
                fast = False

            if window_obj and window_obj.top_ui_mode.get() == "Free":
                free = True
            else:
                free = False

            image_result, quota = screen_translate.CallScreenshots.call_screenshot(image_object,
                                                                                   source_lang,
                                                                                   target_lang,
                                                                                   fast=fast,
                                                                                   free=free)

            if pixel_format == "BGR": 
                image_result = image_result.convert("RGB")
                image_result = swap_red_blue(image_result)
            result = {"image": image_to_string_bmp(image_result)}
            if window_obj:
                if quota:
                    window_obj.update_quota(quota)
                #image_result is a temp image filename, with updated, translated text.
                window_obj.load_image_object(image_result)
                window_obj.curr_image = imaging.ImageItterator.prev()
            return result
        elif config.local_server_api_key_type == "google":
            print "using googl......"
            image_object = load_image(image_data).convert("P", palette=Image.ADAPTIVE)
            image_data = image_to_string(image_object)

            api_ocr_key = config.local_server_ocr_key
            api_translation_key = config.local_server_translation_key
           
            data, raw_output = self.google_ocr(image_data, source_lang, api_ocr_key)
            data = self.process_output(data, raw_output, image_data,
                                       source_lang)
            data = self.translate_output(data, target_lang,
                                         source_lang=source_lang,
                                         google_translation_key=api_translation_key)
            output_image = imaging.ImageModder.write(image_object, data, target_lang)
         
            output_data = {}
            if "sound" in request_output:
                mp3_out = self.text_to_speech(data)
                output_data['sound'] = mp3_out

            if window_obj:
                window_obj.load_image_object(output_image)
                window_obj.curr_image = imaging.ImageItterator.prev()
 
            if pixel_format == "BGR": 
                output_image = output_image.convert("RGB")
                output_image = swap_red_blue(output_image)

            output_data["image"] = image_to_string_bmp(output_image)
            return output_data

        elif config.local_server_api_key_type == "tess_google":
            image_object = load_image(image_data).convert("P", palette=Image.ADAPTIVE)
            image_data = image_to_string(image_object)
 

            api_translation_key = config.local_server_translation_key
            ocr_processor = config.local_server_ocr_processor
            data, source_lang = self.tess_ocr(image_data, source_lang, ocr_processor)
        
            data = self.translate_output(data, target_lang,
                                         source_lang=source_lang,
                                         google_translation_key=api_translation_key)
            output_image = imaging.ImageModder.write(image_object, data, target_lang)
            if window_obj:
                window_obj.load_image_object(output_image)
                window_obj.curr_image = imaging.ImageItterator.prev()
 
            if pixel_format == "BGR": 
                output_image = output_image.convert("RGB")
                output_image = swap_red_blue(output_image)

            return {"image": image_to_string_bmp(output_image)}


    def text_to_speech(self, data):
        texts = list()
        texts2 = list()
        i = 0
        for block in sorted(data['blocks'], key=lambda x: (x['bounding_box']['y'], x['bounding_box']['x'])):
            i+=1
            text = block['translation'][block['target_lang'].lower()]
            this_text = "Textbox "+str(i)+": "+"[] "*3 + text + " "+"[] "*6
            texts.append(this_text)
            texts2.append(text)

        if USE_ESPEAK:
            text_to_say = "".join(texts).replace('"', " [] ")
            cmd = "espeak "+'"'+text_to_say+'"'+" --stdout > tts_out.wav"
            os.system(cmd)#, shell=True)
            wav_data = open("tts_out.wav").read()
        else:
            text_to_say = "".join(texts2).replace('"', " [] ")
            wav_data = TextToSpeech.text_to_speech_api(text_to_say)

        wav_data = self.fix_wav_size(wav_data)
        wav_data = base64.b64encode(wav_data)
        return wav_data

    def fix_wav_size(self, wav):
        def tb(size):
            bs = size%256, int(size/256)%256, int(size/(256**2))%256, int(size/(256**3))%256
            return bytearray(bs)
        size1 = tb(len(wav))
        size2 = tb(len(wav)-44)
        s = bytearray(wav)
        s[4]=size1[0]
        s[5]=size1[1]
        s[6]=size1[2]
        s[7]=size1[3]

        s[40]=size2[0]
        s[41]=size2[1]
        s[42]=size2[2]
        s[43]=size2[3]
        return str(s)


    def google_ocr(self, image_data, source_lang, ocr_api_key):
        doc = {
               "requests": [{
                "image": {"content": image_data},
                "features": [
                  {"type": "DOCUMENT_TEXT_DETECTION"}
                ]
               }]
              }

        #load_image(img_data).show()
        if source_lang:
            doc['requests'][0]['imageContext'] = {"languageHints": [source_lang]}

        body = json.dumps(doc)

        uri = "/v1p1beta1/images:annotate?key="
        uri+= ocr_api_key

        data = self._send_request("vision.googleapis.com", 443, uri, "POST", body)
        output = json.loads(data)

        if output.get("responses", [{}])[0].get("fullTextAnnotation"):
            return output['responses'][0]['fullTextAnnotation'], output
        else:
            return {}, {}

    def tess_ocr(self, image_data, source_lang, ocr_processor):
        if isinstance(ocr_processor, basestring):
            try:
                f = json.loads(open(ocr_processor).read())
            except:
                raise
        if ocr_processor.get("source_lang") and source_lang is None:
            source_lang = ocr_processor['source_lang']

        image = load_image(image_data).convert("P", palette=Image.ADAPTIVE)
        for step in ocr_processor['pipeline']:
            kwargs = step['options']
            if step['action'] == 'reduceToMultiColor':
                image = reduce_to_multi_color(image, kwargs['base'],
                                              kwargs['colors'],
                                              kwargs['threshold'])
            elif step['action'] == 'segFill':
                image = segfill(image, kwargs['base'], kwargs['color'])
            if g_debug_mode == 2:
                image.show()

        if g_debug_mode == 1:
            image.show()
        data = ocr_tools.tess_helper_data(image, lang=source_lang,
                                          mode=6, min_pixels=1)
        for block in data['blocks']:
            block['source_text'] = block['text']
            block['language'] = source_lang
            block['translation'] = ""
            block['text_colors'] = ["FFFFFF"]
            bb = block['bounding_box']
            nb = dict()
            nb['x'] = bb['x1']
            nb['y'] = bb['y1']
            nb['w'] = bb['x2']-bb['x1']
            nb['h'] = bb['y2']-bb['y1']
            block['bounding_box'] = nb
            

        return data, source_lang

    def process_output(self, data, raw_data, image_data, source_lang=None):
        text_colors = list()
        for entry in raw_data.get('responses', []):
            for page in entry['fullTextAnnotation']['pages']:
                for block in page['blocks']:
                    text_colors.append(['ffffff'])

        results = {"blocks": [], "deleted_blocks": []}
        for page in data.get("pages", []):
            for num, block in enumerate(page.get("blocks", [])):
                this_block = {"source_text": [], "language": "", "translation": "",
                              "bounding_box": {"x": 0, "y": 0, "w": 0, "h": 0},
                              "confidence": block.get("confidence"),
                              "text_colors": text_colors[num]
                             }

                if block.get("confidence", 0) <0.8:# and False:
                    continue
                bb = block.get("boundingBox", {}).get("vertices", [])
                this_block['bounding_box']['x'] = bb[0].get('x',0)
                this_block['bounding_box']['y'] = bb[0].get('y', 0)
                this_block['bounding_box']['w'] = bb[2].get('x',0) - bb[0].get('x', 0)
                this_block['bounding_box']['h'] = bb[2].get('y', 0) - bb[0].get('y', 0)
                fix_neg_width_height(this_block['bounding_box'])

                for paragraph in block.get("paragraphs", []):
                    for word in paragraph.get("words", []):
                        for symbol in word.get("symbols", []):
                            if (symbol['text'] == "." and this_block['source_text']\
                                                      and this_block['source_text'][-1] == " "):
                                this_block['source_text'][-1] = "."
                            else:
                                this_block['source_text'].append(symbol['text'])
                        this_block['source_text'].append(" ")
                    this_block['source_text'].append("\n")
                this_block['source_text'] = "".join(this_block['source_text']).replace("\n", " ").strip()
                this_block['original_source_text'] = this_block['source_text']
                results['blocks'].append(this_block)
        return results


    def translate_output(self, data, target_lang, source_lang=None, google_translation_key=None):
        translates = self.google_translate([x['source_text'] for x in\
                                            data['blocks']], target_lang,
                                           google_translation_key=google_translation_key)
        new_blocks = list()
        for i, block in enumerate(data['blocks']):
            if not 'translation' in block or isinstance(block['translation'], basestring):
                block['translation'] = dict()
            block['translation'][target_lang.lower()] =\
                    translates['data']['translations'][i]['translatedText']
            block['target_lang'] = target_lang
            block['language'] = translates['data']['translations'][i]['detectedSourceLanguage']
            if source_lang and source_lang != lang_2_to_3.get(block['language'], ""):
                continue
            new_blocks.append(block)
        data['blocks'] = new_blocks
        return data

    def google_translate(self, strings, target_lang, google_translation_key):
        uri = "/language/translate/v2?key="
        uri+= google_translation_key
        for s in strings:
            try:
                print s
            except:
                pass
        body = '{\n'
        for string in strings:
            body += "'q': "+json.dumps(string)+",\n"
        body += "'target': '"+target_lang+"'\n"
        body +='}'

        data = self._send_request("translation.googleapis.com", 443, uri, "POST", body)
        output = json.loads(data)
        print "==========="

        if "error" in output:
            print output['error']
            return {}

        for x in output['data']['translations']:
            x['translatedText'] = HTMLParser.HTMLParser().unescape(x['translatedText'])
            try:
                print x['translatedText']
            except:
                pass
        
        pairs = [[strings[i], output['data']['translations'][i]['translatedText']] for i in range(len(strings))]
        for intext, outtext in pairs:
            doc = {"target_lang": target_lang,
                   "text": intext,
                   "translation": outtext,
                   "auto": True,
                  }
        return output

    def _send_request(self, host, port, uri, method, body=None):
        conn = httplib.HTTPSConnection(host, port)
        if body is not None:
            conn.request(method, uri, body)
        else:
            conn.request(method, uri)
        response = conn.getresponse()
        return response.read()



def start_api_server(window_object):
    global server_thread
    global window_obj
    if config.local_server_enabled:
        #start thread with this server in it:
        window_obj = window_object
        server_thread = threading.Thread(target=start_api_server2)
        server_thread.start()

def kill_api_server():  
    global httpd_server
    if config.local_server_enabled:
        httpd_server.shutdown()

def start_api_server2():
    global httpd_server
    host = config.local_server_host
    port = config.local_server_port      
    server_class = BaseHTTPServer.HTTPServer
    httpd_server = server_class((host, port), APIHandler)
    print "server start"
    try:
        httpd_server.serve_forever()
    except KeyboardInterrupt:
        pass

 
def main():
    global g_debug_mode
    if not config.load_init():
        return
    host = config.local_server_host
    port = config.local_server_port 
    server_class = BaseHTTPServer.HTTPServer
    httpd = server_class((host, port), APIHandler)
    if "--debug-extra" in sys.argv:
        g_debug_mode = 2
    elif "--debug" in sys.argv:
        g_debug_mode = 1

    print "server start"
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    httpd.server_close()
    print 'end'

if __name__=="__main__":
    main()
