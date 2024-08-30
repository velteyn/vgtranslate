#!/usr/bin/env python2

from setuptools import find_packages, setup

__VERSION__ = "1.0.0"

def main(args=None):
    README = open("./README.md").read()

    setup_required_packages = []

    required_packages = ["Pillow==10.4.0", "numpy==2.1.0",
                         "opencv-python==3.4.18.65",
                         "pytesseract==0.2.4",
                         "pyttsx",
                         "pyocr==0.8.5"#, "gender-guess"
                         ]

    test_required_packages = ["nose", "coverage"]

    settings = dict(name="vgtranslate",
                    version=__VERSION__,
                    description="vgtranslate",
                    long_description=README,
                    classifiers=["Programming Language :: Python", ],
                    author="",
                    author_email="",
                    url="",
                    keywords="vgtranslate",
                    packages=find_packages(),
                    include_package_data=True,
                    zip_safe=False,
                    install_requires=required_packages,
                    tests_require=test_required_packages,
                    test_suite="nose.collector",
                    setup_requires=setup_required_packages,
                    entry_points="""\
                        [console_scripts] 
                        vg_translate_serve=vg_translate.serve:main
                        """,
                    )
    if args:
        settings['script_name'] = __file__
        settings['script_args'] = args
    setup(**settings)


if __name__ == "__main__":
    main()
