import json
import imaging

server_host = "ztranslate"
server_port = 8888
user_api_key = ""
default_target = "en"

local_server_enabled = False
local_server_host = "localhost"
local_server_port = 4404
local_server_ocr_key = ""
local_server_translation_key = ""
local_server_api_key_type = "google"
local_server_ocr_processor = ""

font = "RobotoCondensed-Bold.ttf"

def load_init():
    global server_host
    global server_port
    global user_api_key
    global default_target
    global local_server_enabled
    global local_server_host
    global local_server_port
    global local_server_ocr_key
    global local_server_translation_key
    global local_server_api_key_type
    global local_server_ocr_processor
    global font

    try:
        config_file = json.loads(open("./config.json").read())
    except Exception as e:
        print "Invalid config file specification:"
        print e.message
        return False

    if "server_host" in config_file:
        server_host = config_file['server_host']    
    if "server_port" in config_file:
        server_port = config_file['server_port']    
    if "user_api_key" in config_file:
        user_api_key = config_file['user_api_key']    
    if "default_target" in config_file:
        default_target = config_file['default_target']    

    if "local_server_enabled" in config_file:
        local_server_enabled = config_file['local_server_enabled']
    if "local_server_host" in config_file:
        local_server_host = config_file['local_server_host']
    if "local_server_port" in config_file:
        local_server_port = config_file['local_server_port']

    if "local_server_ocr_key" in config_file:
        local_server_ocr_key = config_file['local_server_ocr_key']
    if "local_server_translation_key" in config_file:
        local_server_translation_key = config_file['local_server_translation_key']
    if "local_server_api_key_type" in config_file:
        local_server_api_key_type = config_file['local_server_api_key_type']

    if "local_server_ocr_processor" in config_file:
        local_server_ocr_processor = config_file['local_server_ocr_processor']

    if "font" in config_file:
        font = config_file['font']
    print "using font: "+font
    imaging.load_font(font)
    print "config loaded"
    print "===================="
    #print user_api_key
    return True

def write_init():
    obj = {"server_host": server_host,
           "server_port": server_port,
           "user_api_key": user_api_key,
           "default_target": default_target,
           "local_server_enabled": local_server_enabled,
           "local_server_host": local_server_host,
           "local_server_port": local_server_port,
           "local_server_ocr_key": local_server_ocr_key,
           "local_server_translation_key": local_server_translation_key,
           "local_server_api_key_type": local_server_api_key_type,
           "font": font
    }
    config_file = open("./config.json", "w")
    config_file.write(json.dumps(obj, indent=4))

