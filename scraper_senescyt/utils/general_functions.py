from importlib import resources
from pathlib import Path
import re

import ddddocr

ocr = ddddocr.DdddOcr(show_ad=False)


def decodificar_captcha(path_img):
    with open(path_img, 'rb') as f:
        img_bytes = f.read()
    texto = ocr.classification(img_bytes)
    texto = re.sub(r'[^A-Za-z0-9]', '', texto)
    texto = texto.strip()
    print(f'🔤 CAPTCHA: "{texto}"')
    return texto

def list_in_string(list_objects):
    return tuple(f"'{value}'" for value in list_objects)
