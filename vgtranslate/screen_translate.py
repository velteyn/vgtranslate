import imaging
import server_client

class CallScreenshots:
    @classmethod
    def call_screenshot(cls, image_object, source_lang=None, 
                        target_lang='en', fast=None, free=None):
        return cls.call_screenshot_api(image_object, source_lang,
                                       target_lang, fast, free)

    @classmethod
    def call_screenshot_api(cls, image_object=None, source_lang=None, 
                            target_lang='en', fast=None, free=None):
        #save image to user storage
        stored_filename = imaging.ImageSaver.save_image(image_object)
        result = server_client.ServerClient.call_server(image_object, 
                                                        source_lang, 
                                                        target_lang,
                                                        fast, free)
        quota = result.get("quota", 0)
        output_image = imaging.ImageModder.write(image_object, result, target_lang)
        imaging.ImageSaver.save_image(output_image, stored_filename)
        return output_image, quota


