import codecs
import csv
import json
import logging
import re
from io import BytesIO, StringIO
from typing import Any, TypeAlias
import chardet

import numpy as np
import numpy.typing as npt
import pandas as pd
from findpeaks import findpeaks  # type: ignore
from requests import Response, get
from .filetypes import filetypes
from typing import Tuple

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


def multi_sub(pairs: list[Tuple[str, str]], s: str):
    def repl_func(m):
        return next(
            repl for (_, repl), group in zip(pairs, m.groups()) if group is not None
        )

    pattern = "|".join("({})".format(patt) for patt, _ in pairs)
    return re.sub(pattern, repl_func, s, flags=re.U)


def download_file(url: URL) -> BytesIO | None:
    """
    Download file from given url and return it as an in-memory buffer
    """
    try:
        response: Response = get(url, timeout=10)
    except Exception as e:
        logger.error(e)
        return None
    file: BytesIO = BytesIO(response.content)
    file.seek(0)
    return file


def find_peaks(file: BytesIO) -> npt.NDArray | None:
    """
    Find peaks in second array of csv-like data and return as numpy array.

    Peaks are filtered by their rank and height returned by findpeaks.
    Return None if none were found
    """
    try:
        data = np.loadtxt(file, delimiter=",")[:, 1]
        fp = findpeaks(method="topology", lookahead=2, denoise="bilateral")
        if (result := fp.fit(data / np.max(data))) is not None:
            df: pd.DataFrame = result["df"]
        else:
            return None

        filtered_pos: npt.NDArray = df.query(
            "peak == True & rank != 0 & rank <= 40 & y >= 0.005"
        )  # type: ignore
        return filtered_pos["x"].to_numpy()  # type:ignore
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
        x_linspace = np.linspace(x_range[0], x_range[1], line_count - 1)
        y_counts: list[float] = []

        with file as f:
            # [float(s) for s in f.readline().split()]
            header: bytes = f.readline()
            for line in f:
                y_counts.append(float(line.strip()))

        output = np.vstack((x_linspace, np.array(y_counts))).T

        sio: StringIO = StringIO()
        csvWriter = csv.writer(sio, delimiter=",")
        csvWriter.writerows(output)

        sio.seek(0)

        bio: BytesIO = BytesIO(sio.read().encode("utf8"))

        sio.close()

        bio.name = f'{filename.rsplit(".", 1)[0]}.csv'
        bio.seek(0)

        return bio
    except Exception as e:
        logger.error(e)
        return None


def construct_metadata(
    init, peak_data: npt.NDArray
) -> dict[str, list[dict[str, str]]] | None:
    """
    Construct JSON object from existing spectrum metadata and peak metadata from processing
    """
    peak_metadata: dict[str, list[dict[str, str]]] = {
        "peaks": [{"position": str(i)} for i in peak_data]
    }

    if isinstance(init, str):
        return {**json.loads(init), **peak_metadata}
    elif isinstance(init, dict):
        return {**init, **peak_metadata}
    else:
        return None


def convert_to_csv(file: BytesIO, filename: str) -> BytesIO | None:
    try:
        enc = chardet.detect(file.read())["encoding"] or "utf-8"
        file.seek(0)

        with file as f:
            filetype = None
            for ft in filetypes:
                res_list = []
                for r in filetypes[ft]["line_matchers"]:
                    line = f.readline().decode(enc)
                    res = re.match(r, line.strip(), flags=re.U)
                    res_list.append(res)
                f.seek(0)
                if None not in res_list:
                    filetype = ft
                    break
            if filetype is not None:
                if filetype == "xrf.dat":
                    converted = convert_dat(f, filename)
                    return converted

                header, body, *footer = np.split(
                    f.readlines(), np.asarray(filetypes[filetype]["split_indices"])
                )

                replacements = [
                    (filetypes[filetype]["line_delimiter"], ","),
                    (filetypes[filetype]["decimal_delimiter"], "."),
                ]

                sio = StringIO()
                csv_writer = csv.writer(sio, delimiter=",")

                for line in body:
                    parsed_line = multi_sub(replacements, line.decode(enc).strip())
                    csv_writer.writerow([i.strip() for i in parsed_line.split(",")])

                sio.seek(0)

                bio: BytesIO = BytesIO(sio.read().encode("utf8"))

                sio.close()

                bio.name = f'{filename.rsplit(".", 1)[0]}.csv'
                bio.seek(0)

                return bio

            else:
                logger.error("Error! Unsupported filetype")
                return None

    except Exception as e:
        logger.error(e)
        return None
