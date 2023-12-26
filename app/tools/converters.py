import csv
import json
import logging
import re
from io import BytesIO, StringIO
from typing import Any, Tuple, TypeAlias

import chardet
import numpy as np
from requests import Response, get

from .filetypes import filetypes

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


def multi_sub(sub_pairs: list[Tuple[str, str]], string: str):
    def repl_func(m):
        return next(
            repl for (_, repl), group in zip(sub_pairs, m.groups()) if group is not None
        )

    pattern = "|".join("({})".format(patt) for patt, _ in sub_pairs)
    return re.sub(pattern, repl_func, string, flags=re.U)


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
        csv_writer = csv.writer(sio, delimiter=",")
        csv_writer.writerows(output)

        sio.seek(0)

        bio: BytesIO = BytesIO(sio.read().encode("utf8"))

        sio.close()

        bio.name = f'{filename.rsplit(".", 1)[0]}.csv'
        bio.seek(0)

        return bio
    except Exception as e:
        logger.error(e)
        return None


def detect_filetype(file: BytesIO):
    try:
        enc = detect_encoding(file)
        filetype = None
        for ft in filetypes:
            res_list = []
            for r in filetypes[ft]["line_matchers"]:
                line = file.readline().decode(enc)
                res = re.match(r, line.strip())
                res_list.append(res)
            file.seek(0)
            if None not in res_list:
                filetype = filetypes[ft]
                break

        return filetype
    except Exception as e:
        logger.error(f"Error detecting filetype: {e}")
        return None


def detect_encoding(file: BytesIO):
    enc = chardet.detect(file.read())["encoding"] or "utf-8"
    file.seek(0)
    return enc


def convert_to_csv(file: BytesIO, filename: str) -> BytesIO | None:
    try:
        with file as f:
            filetype = detect_filetype(f)
            encoding = detect_encoding(f)

            if filetype is None:
                logger.error("Error! Unsupported filetype")
                return None

            if filetype["method"] == "xrf_single_column":
                converted = convert_dat(f, filename)
                return converted

            header, body, *footer = np.split(
                f.readlines(), np.asarray(filetype["split_indices"])
            )

            replacements = [
                (filetype["field_delimiter"], ","),
                (filetype["radix_point"], "."),
            ]

            sio = StringIO()
            csv_writer = csv.writer(sio, delimiter=",")

            for line in body:
                parsed_line = multi_sub(replacements, line.decode(encoding).strip())
                all_cols = [i.strip() for i in parsed_line.split(",")]
                csv_writer.writerow([all_cols[i] for i in filetype["columns"]])

            sio.seek(0)

            bio: BytesIO = BytesIO(sio.read().encode("utf8"))

            sio.close()

            bio.name = f'{filename.rsplit(".", 1)[0]}.csv'
            bio.seek(0)

            return bio

    except Exception as e:
        logger.error(e)
        return None
