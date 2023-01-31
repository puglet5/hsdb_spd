import pandas as pd
import numpy as np
import io
import re
import os
import shutil
import requests


def download_file(url):
    """
    Downloads file from given url and return it as memory buffer
    """
    try:
        response = requests.get(url)
        file = io.BytesIO(response.content)
        return file
    except Exception as e:
        return e


def convert_dpt(file):
    """
    Converts FTIR .1.dpt and .0.dpt files to .csv
    """
    df = pd.read_csv(file, header=None, index_col=False)
    file.flush()
    file.seek(0)
    s_buf = io.StringIO()
    df.to_csv(s_buf, index=False, header=False, sep=",")
    return s_buf
