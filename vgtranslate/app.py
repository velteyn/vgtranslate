import kivy

from kivy.app import App
from kivy.uix.label import Label

class VGTranslateApp(App):
    def build(self):
        return Label(text="hello world!")

def main():
    VGTranslateApp().run()

if __name__=='__main__':
    main()
