import json
import csv
import codecs
import numpy as np
import numpy.typing as npt
import pandas as pd
import logging

from findpeaks import findpeaks
from typing import Any, TypeAlias
from requests import Response, get
from io import BytesIO, StringIO

logger = logging.getLogger(__name__)

URL: TypeAlias = str


def validate_json(json_data: Any) -> bool:
    if isinstance(json_data, dict):
        return True
    try:
        json.loads(str(json_data))
    except (ValueError, TypeError):
        return False
    return True


def download_file(url: URL) -> BytesIO | None:
    """
    Download file from given url and return it as an in-memory buffer
    """
    try:
        response: Response = get(url)
    except Exception as e:
        logger.error(e)
        return None
    file: BytesIO = BytesIO(response.content)
    file.seek(0)
    return file


def validate_csv(file: BytesIO, filename: str) -> BytesIO | None:
    try:
        dialect = csv.Sniffer().sniff(file.read(1024).decode('utf-8'))
        file.seek(0)
        has_header: bool = csv.Sniffer().has_header(file.read(1024).decode('utf-8'))
        file.seek(0)
        if has_header:
            file.close()
            return None

        csv_data = csv.reader(codecs.iterdecode(file, 'utf-8'), dialect)

        sio: StringIO = StringIO()

        writer = csv.writer(sio, dialect='excel', delimiter=',')
        for row in csv_data:
            if row.count(',') + 1 > 2:
                sio.close()
                return None
            writer.writerow(row)

        sio.seek(0)
        bio: BytesIO = BytesIO(sio.read().encode('utf8'))

        sio.close()

        bio.name = f'{filename.rsplit(".", 2)[0]}.csv'
        bio.seek(0)

        return bio
    except Exception as e:
        logger.error(e)
        return None


def find_peaks(file: BytesIO) -> npt.NDArray | None:
    """
    Find peaks in second array of csv-like data and return as numpy array.

    Peaks are filtered by their rank and height returned by findpeaks.
    Return None if none were found
    """
    try:
        data = np.loadtxt(file, delimiter=",")[:, 1]
        fp = findpeaks(method='topology', lookahead=2, denoise="bilateral")
        if (result := fp.fit(data / np.max(data))) is not None:
            df: pd.DataFrame = result["df"]
        else:
            return None

        filtered_pos: npt.NDArray = df.query('peak == True & rank != 0 & rank <= 40 & y >= 0.005')[
            "x"].to_numpy()
        return filtered_pos
    except Exception as e:
        logger.error(e)
        return None


def convert_dpt(file: BytesIO, filename: str) -> BytesIO | None:
    """
    Convert FTIR .1.dpt and .0.dpt files to .csv
    """
    try:
        csv_data = csv.reader(codecs.iterdecode(file, 'utf-8'))

        sio: StringIO = StringIO()

        writer = csv.writer(sio, dialect='excel', delimiter=',')
        for row in csv_data:
            writer.writerow(row)

        sio.seek(0)
        bio: BytesIO = BytesIO(sio.read().encode('utf8'))

        sio.close()

        bio.name = f'{filename.rsplit(".", 2)[0]}.csv'
        bio.seek(0)

        return bio
    except Exception as e:
        logger.error(e)
        return None


def convert_dat(file: BytesIO, filename: str) -> BytesIO | None:
    """
    Convert Bruker's Tracer XRF .dat files to .csv
    """
    try:
        line_count: int = sum(1 for line in file.readlines() if line.rstrip())
        file.seek(0)

        x_range: list[int] = [0, 40]
        x_linspace = np.linspace(x_range[0], x_range[1], line_count-1)
        y_counts: list[float] = []

        with file as f:
            # [float(s) for s in f.readline().split()]
            header: bytes = f.readline()
            for line in f:
                y_counts.append(float(line.strip()))

        output = np.vstack((x_linspace, np.array(y_counts))).T

        sio: StringIO = StringIO()
        csvWriter = csv.writer(sio, delimiter=',')
        csvWriter.writerows(output)

        sio.seek(0)

        bio: BytesIO = BytesIO(sio.read().encode('utf8'))

        sio.close()

        bio.name = f'{filename.rsplit(".", 2)[0]}.csv'
        bio.seek(0)

        return bio
    except Exception as e:
        logger.error(e)
        return None


def construct_metadata(init, peak_data: npt.NDArray) -> dict | None:
    """
    Construct JSON object from existing spectrum metadata and peak metadata from processing
    """
    peak_metadata: dict[str, list[dict[str, str]]] = {
        "peaks": [{"position": str(i)} for i in peak_data]}
    if isinstance(init, str):
        return {**json.loads(init), **peak_metadata}
    elif isinstance(init, dict):
        return {**init, **peak_metadata}
    else:
        return None
