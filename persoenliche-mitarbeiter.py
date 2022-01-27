#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import os
from datetime import date
from pathlib import Path

import pdftotext
import requests

if __name__ == '__main__':
    # script_dir = os.path.dirname(__file__)
    out_dir = os.path.join(Path.home(), 'persoenliche-mitarbeiter')
    url = 'https://www.parlament.ch/centers/documents/de/liste-persoenliche-mitarbeiter-NR.pdf'
    response = requests.get(url)
    with open(os.path.join(out_dir, f"{date.today()}-nr.pdf"), mode='wb') as f:
        f.write(response.content)
    b = io.BytesIO(response.content)
    pdf = pdftotext.PDF(b)
    with open(os.path.join(out_dir, f"{date.today()}-nr.txt"), encoding='utf-8', mode='w') as f:
        f.write("\n\n".join(pdf))

    url = 'https://www.parlament.ch/centers/documents/de/liste-persoenliche-mitarbeiter-SR.pdf'
    response = requests.get(url)
    with open(os.path.join(out_dir, f"{date.today()}-sr.pdf"), mode='wb') as f:
        f.write(response.content)
    b = io.BytesIO(response.content)
    pdf = pdftotext.PDF(b)
    with open(os.path.join(out_dir, f"{date.today()}-sr.txt"), encoding='utf-8', mode='w') as f:
        f.write("\n\n".join(pdf))
