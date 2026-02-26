from PIL import Image
import base64
import time
import io
import sys
import os
import shlex
import numpy as np
import subprocess

from util import get_color_counts_simple, reduce_to_multi_color, segfill

if os.name == "nt":
    import pyocr_util 
else:
    import pytesseract


lang_to_tesseract_lang = {
    "deu": "deu",
    "eng": "eng",
    "jpn": "jpn"
}


def setup_pytesseract(lang="eng"):
    if lang is None:
        lang = "eng"

    if os.name == "nt": 
        pyocr_util.load_tesseract_dll(lang=lang)
    else:
        #linux here
        pytesseract.pytesseract.tesseract_cmd = r'tesseract'


def tess_helper(image, lang=None, mode=None,min_pixels=1):
    if os.name == "nt":
        return tess_helper_windows(image, lang, mode, min_pixels)
    else:
        return tess_helper_linux(image, lang, mode, min_pixels)

def tess_helper_data(image, lang=None, mode=None,min_pixels=1):
    if os.name == "nt":
        return tess_helper_data_windows(image, lang, mode, min_pixels)
    else:
        return tess_helper_data_linux(image, lang, mode, min_pixels)


def tess_helper_windows(image, lang=None, mode=None,min_pixels=1):
    setup_pytesseract(lang)

    if mode is None:
        mode = 6

    t_ = time.time()
    pc = get_color_counts_simple(image, ["FFFFFF"], 2)

    if min_pixels and pc < min_pixels:
        return list()
    x = pyocr_util.image_to_boxes(image, lang=lang, mode=mode)
    print(['ocr time', time.time()-t_])

    found_chars = list()
    for word_box in x:     
        word = word_box.content
        box = word_box.position

        l = len(word)
        w = box[1][0] - box[0][0]
            
        for i, char in enumerate(word):
            found_chars.append([char, [box[0][0]+((i)*w)/l, box[0][1], 
                                       box[0][0]+((i+1)*w)/l, box[1][1]]])
    
    data = list()
    curr_pos = None
    curr_box = None
    found_lines = list()
    curr_line = ""
    char_h = 0
    char_w = 0
    if found_chars:
        for entry in found_chars:
            char = entry[0]
            coords = entry[1]

            this_char_h = coords[3]-coords[1]
            this_char_w = coords[2]-coords[0]
            char_h = max(char_h, this_char_h)
            char_w = max(char_w, this_char_w)

            if curr_pos is None:
                curr_pos = coords
                curr_box = coords
                curr_line = char
            else:
                if coords[0] > last_x-char_w and\
                   curr_box[0]-char_w/2 < coords[0] < curr_box[2] + (char_w)*3 and\
                   curr_box[0]-char_w/2 < coords[2] < curr_box[2] + (char_w)*4 and\
                   curr_box[1]-char_h < coords[1] < curr_box[3] + (char_h) and\
                   curr_box[1]-char_h < coords[3] < curr_box[3]+char_h:
                    #another character to add:
                    if curr_box[0] > coords[0]:
                        curr_box[0]  = coords[0]
                    if curr_box[1] > coords[1]:
                        curr_box[1]  = coords[1]
                    if curr_box[2] < coords[2]:
                        curr_box[2]  = coords[2]
                    if curr_box[3] < coords[3]:
                        curr_box[3]  = coords[3]

                    curr_pos = coords
                    curr_line+=char
                else:
                    found_lines.append([curr_line, curr_box])
                    curr_pos = coords
                    curr_box = coords
                    curr_line = char
                    char_h = 0
                    char_w = 0
            last_x = coords[0]
        if curr_line:
            found_lines.append([curr_line, curr_box])
    #for c in found_lines:
    #    print c
    return found_lines
    

def tess_helper_linux(image, lang=None, mode=None, min_pixels=1):
    setup_pytesseract()

    pc = get_color_counts_simple(image, ["FFFFFF"], 2)

    if min_pixels and pc < min_pixels:
        return list()

    config_arg = ""
    if mode is not None:
        config_arg += " --psm "+str(mode)

    if not config_arg:
        config_arg = ""

    for i in range(2):
        try:
            if lang:
                lang = lang_to_tesseract_lang[lang]
                x = pytesseract.image_to_boxes(image, lang=lang, config=config_arg)
            else:
                x = pytesseract.image_to_boxes(image, config=config_arg)
            break
        except Exception as e:
            if type(e) == KeyboardInterrupt:
                raise

            if i == 1:
                raise
            print('tttttttttttttttttttttttt')
            setup_pytesseract()


    h = image.height
    data = list()
    curr_pos = None
    curr_box = None
    found_lines = list()
    curr_line = ""
    char_h = 0
    char_w = 0
    last_x = None
    if x.strip():
        for line in x.split("\n"):
            if not line.strip():
                continue
            split = line.split(" ")
            if len(split) < 6:
                continue
            char = split[0]
            coords = [int(i) for i in split[1:5]]

            coords = [coords[0], coords[3], coords[2], coords[1]]
            coords[1] = h-coords[1]
            coords[3] = h-coords[3]

            this_char_h = coords[3]-coords[1]
            this_char_w = coords[2]-coords[0]
            char_h = max(char_h, this_char_h)
            char_w = max(char_w, this_char_w)

            if curr_pos is None:
                curr_pos = coords
                curr_box = coords
                curr_line = char
            else:
                if coords[0] > last_x-char_w and\
                   curr_box[0]-char_w/2 < coords[0] < curr_box[2] + (char_w)*3 and\
                   curr_box[0]-char_w/2 < coords[2] < curr_box[2] + (char_w)*4 and\
                   curr_box[1]-char_h < coords[1] < curr_box[3] + (char_h) and\
                   curr_box[1]-char_h < coords[3] < curr_box[3]+char_h:
                    #another character to add:
                    if curr_box[0] > coords[0]:
                        curr_box[0]  = coords[0]
                    if curr_box[1] > coords[1]:
                        curr_box[1]  = coords[1]
                    if curr_box[2] < coords[2]:
                        curr_box[2]  = coords[2]
                    if curr_box[3] < coords[3]:
                        curr_box[3]  = coords[3]

                    curr_pos = coords
                    curr_line+=char
                else:
                    found_lines.append([curr_line, curr_box])
                    curr_pos = coords
                    curr_box = coords
                    curr_line = char
                    char_h = 0
                    char_w = 0
            last_x = coords[0]

        if curr_line:
            found_lines.append([curr_line, curr_box])
    for l in found_lines:
        print(l)
    return found_lines




def tess_helper_data_linux(image, lang=None, mode=None, min_pixels=1):
    setup_pytesseract()
    pc = get_color_counts_simple(image, ["FFFFFF"], 2)

    if min_pixels and pc < min_pixels:
        return {"blocks": []}

    config_arg = ""
    if mode is not None:
        config_arg += " --psm "+str(mode)

    if not config_arg:
        config_arg = ""
  
    for i in range(2):
        try:
            if lang:
                lang = lang_to_tesseract_lang[lang]
                x = pytesseract.image_to_data(image, lang=lang, config=config_arg)
            else:
                x = pytesseract.image_to_data(image, config=config_arg)
            break
        except Exception as e:
            if type(e) == KeyboardInterrupt:
                raise

            if i == 1:
                raise
            print('failed tesseract, retying...')
            setup_pytesseract()
 
    #x now holds the tesseract computed data in table csv (tab) format:
    results = {"blocks": []}
    for i, line in enumerate(x.split("\n")):
        if i > 0:
            split = line.split("\t")
            
            if len(split) < 11:
                continue
            level, page_num, block_num, par_num, line_num, word_num, left, top, width, height, conf = split[:11]
            if len(split) > 11:
                text = split[11]
            else:
                text = ""
            block_num = int(block_num, 10)
            left = int(left, 10)
            top = int(top, 10)
            width = int(width, 10)
            height = int(height, 10)
            

            while block_num > len(results['blocks']) -1:
                results['blocks'].append({})
            curr_block = results['blocks'][block_num]

            if not curr_block.get('text'):
                curr_block['text'] = list()
            curr_block['text'].append(text)

            curr_bounding = {"x1": left, "y1": top, 
                             "x2": left+width, "y2": height+top}
 
            if not curr_block.get('bounding_box'):
                curr_block['bounding_box'] = curr_bounding
            else:
                if curr_bounding['x1'] < curr_block['bounding_box']['x1']:
                    curr_block['bounding_box']['x1'] = curr_bounding['x1']
                if curr_bounding['y1'] < curr_block['bounding_box']['y1']:
                    curr_block['bounding_box']['y1'] = curr_bounding['y1']
                if curr_bounding['x2'] > curr_block['bounding_box']['x2']:
                    curr_block['bounding_box']['x2'] = curr_bounding['x2']
                if curr_bounding['y2'] > curr_block['bounding_box']['y2']:
                    curr_block['bounding_box']['y2'] = curr_bounding['y2']

    out_res = list()
    for res in results['blocks']:
        if res: 
            res['text'] = " ".join(res['text'])
            out_res.append(res)
    results['blocks'] = out_res
    return results






def tess_helper_data_windows(image, lang=None, mode=None, min_pixels=1):
    setup_pytesseract(lang)

    if mode is None:
        mode = 6

    t_ = time.time()
    pc = get_color_counts_simple(image, ["FFFFFF"], 2)

    if min_pixels and pc < min_pixels:
        return {"blocks": []}
    x = pyocr_util.image_to_data(image, lang=lang, mode=mode)
    print(['ocr time', time.time()-t_])

    #x now holds the tesseract computed data in table csv (tab) format:
    results = {"blocks": []}
    for i, line in enumerate(x.split("\n")):
        if i > 0:
            line = line[:-1]

            split = line.split("\t")
            if len(split) < 12:
                continue
            level, page_num, block_num, par_num, line_num, word_num, left, top, width, height, conf, text = split[:12]
            block_num = int(block_num, 10)
            while block_num > len(results['blocks']) -1:
                results['blocks'].append({})
            curr_block = results['blocks'][block_num]

            if not curr_block.get('text'):
                curr_block['text'] = list()
            curr_block['text'].append(text)
            if curr_block.get('confidence') is None:
                curr_block['confidence'] = conf
            elif curr_block['confidence'] > conf:
                curr_block['confidence'] = conf

            curr_bounding = {"x1": left, "y1": top, 
                             "x2": left+width, "y2": height+top}
 
            if not curr_block.get('bounding_box'):
                curr_block['bounding_box'] = curr_bounding
            else:
                if curr_bounding['x1'] < curr_block['bounding_box']['x1']:
                    curr_block['bounding_box']['x1'] = curr_bounding['x1']
                if curr_bounding['y1'] < curr_block['bounding_box']['y1']:
                    curr_block['bounding_box']['y1'] = curr_bounding['y1']
                if curr_bounding['x2'] > curr_block['bounding_box']['x2']:
                    curr_block['bounding_box']['x2'] = curr_bounding['x2']
                if curr_bounding['y2'] > curr_block['bounding_box']['y2']:
                    curr_block['bounding_box']['y2'] = curr_bounding['y2']

    out_res = list()
    for res in results['blocks']:
        if res:
            out_res.append(res)
    results['blocks'] = out_res
    return results





def tess_helper_server(image, lang=None, mode=None):
    setup_pytesseract()

    config_arg = ""
    if mode is not None:
        config_arg += " --psm "+str(mode)

    if not config_arg:
        config_arg = ""

    if lang:
        lang = lang_to_tesseract_lang[lang]
        x = pytesseract.image_to_boxes(image, lang=lang, config=config_arg)
    else:
        x = pytesseract.image_to_boxes(image, config=config_arg)
    h = image.height
    data = list()
    curr_pos = None
    curr_box = None
    found_lines = list()
    curr_line = ""
    char_h = 0
    char_w = 0
    last_x = None
    if x.strip():
        for line in x.split("\n"):
            if not line.strip():
                continue
            split = line.split(" ")
            if len(split) < 6:
                continue
            char = split[0]
            coords = [int(i) for i in split[1:5]]
            coords = [coords[0], coords[3], coords[2], coords[1]]
            coords[1] = h-coords[1]
            coords[3] = h-coords[3]

            this_char_h = coords[3]-coords[1]
            this_char_w = coords[2]-coords[0]
            char_h = max(char_h, this_char_h)
            char_w = max(char_w, this_char_w)
            if curr_pos is None:
                curr_pos = coords
                curr_box = coords
                curr_line = char
            else:  
                
                if coords[0] > last_x-char_w and\
                   curr_box[0]-char_w/2 < coords[0] < curr_box[2] + (char_w)*3 and\
                   curr_box[0]-char_w/2 < coords[2] < curr_box[2] + (char_w)*4 and\
                   curr_box[1]-char_h < coords[1] < curr_box[3] + (char_h) and\
                   curr_box[1]-char_h < coords[3] < curr_box[3]+char_h:
                    #another character to add:
                    if curr_box[0] > coords[0]:
                        curr_box[0]  = coords[0]
                    if curr_box[1] > coords[1]:
                        curr_box[1]  = coords[1]
                    if curr_box[2] < coords[2]:
                        curr_box[2]  = coords[2]
                    if curr_box[3] < coords[3]:
                        curr_box[3]  = coords[3]

                    curr_pos = coords
                    curr_line+=char
                else:
                    found_lines.append([curr_line, curr_box])
                    curr_pos = coords
                    curr_box = coords
                    curr_line = char
                    char_h = 0 
                    char_w = 0
            last_x = coords[0]

        if curr_line:
            found_lines.append([curr_line, curr_box])
    return found_lines

_easyocr_readers = {}

def get_easyocr_reader(lang):
    import easyocr
    # map jpn to ja
    if lang == 'jpn':
        langs = ('ja',)
    elif lang == 'eng':
        langs = ('en',)
    else:
        langs = (lang,) if isinstance(lang, str) else tuple(lang)

    if langs not in _easyocr_readers:
        _easyocr_readers[langs] = easyocr.Reader(list(langs), gpu=False)
    return _easyocr_readers[langs]

def easyocr_helper(image, lang='jpn'):
    reader = get_easyocr_reader(lang)
    # Detail=1 returns [[bbox], text, confidence]
    result = reader.readtext(np.array(image.convert('RGB')), detail=1)

    found_lines = list()
    for (bbox, text, prob) in result:
        # bbox is [[x, y], [x, y], [x, y], [x, y]]
        x1 = min(p[0] for p in bbox)
        y1 = min(p[1] for p in bbox)
        x2 = max(p[0] for p in bbox)
        y2 = max(p[1] for p in bbox)
        found_lines.append([text, [int(x1), int(y1), int(x2), int(y2)]])

    return found_lines

_manga_ocr = None

def get_manga_ocr():
    global _manga_ocr
    if _manga_ocr is None:
        from manga_ocr import MangaOcr
        _manga_ocr = MangaOcr()
    return _manga_ocr

def manga_ocr_helper(image):
    mocr = get_manga_ocr()
    text = mocr(image)

    # MangaOCR doesn't provide bounding boxes, so we return the whole image as a block
    found_lines = [[text, [0, 0, image.width, image.height]]]

    return found_lines

def easyocr_helper_data(image, lang='jpn'):
    reader = get_easyocr_reader(lang)
    result = reader.readtext(np.array(image.convert('RGB')), detail=1)

    results = {"blocks": []}
    for (bbox, text, prob) in result:
        x1 = min(p[0] for p in bbox)
        y1 = min(p[1] for p in bbox)
        x2 = max(p[0] for p in bbox)
        y2 = max(p[1] for p in bbox)

        block = {
            "text": text,
            "bounding_box": {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)},
            "confidence": prob
        }
        results["blocks"].append(block)
    return results

def manga_ocr_helper_data(image):
    mocr = get_manga_ocr()
    text = mocr(image)

    results = {"blocks": [
        {
            "text": text,
            "bounding_box": {"x1": 0, "y1": 0, "x2": image.width, "y2": image.height},
            "confidence": 1.0
        }
    ]}
    return results

def main():
    image= Image.open("images.png").convert("P", palette=Image.ADAPTIVE)
    img = reduce_to_multi_color(image, "000000", [["FFFFFF", "FFFFFF"]], 8)
    img.show()
    img.save("out.png")
    tess_helper(image, lang="jpn", mode=3, min_pixels=2)

if __name__=='__main__':
    main()
