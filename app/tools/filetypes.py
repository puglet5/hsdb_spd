import re
from typing import Pattern, Tuple, TypedDict


class Filetype(TypedDict):
    columns: Tuple[int, ...]
    method: str
    field_delimiter: str
    radix_point: str
    split_indices: Tuple[int, ...]
    line_matchers: list[Pattern[str]]


filetypes: dict[str, Filetype] = {
    "libs.spectable": {
        "columns": (0, 1),
        "method": "libs",
        "radix_point": "\\,",
        "field_delimiter": "\t",
        "split_indices": (2,),
        "line_matchers": [
            re.compile("^Wavelenght[ \t]+Spectrum$"),
            re.compile("^Integration delay[ \t]+[+-]?([0-9]*[,])?[0-9]+$"),
            re.compile("^[+-]?([0-9]*[,])?[0-9]+\t[+-]?([0-9]*[,])?[0-9]+$"),
        ],
    },
    "libs.spec": {
        "columns": (0, 1),
        "method": "libs",
        "radix_point": "\\,",
        "field_delimiter": "\t",
        "split_indices": (2,),
        "line_matchers": [
            re.compile("^[0-9]+$"),
            re.compile("^[0-9]+$"),
            re.compile("^[+-]?([0-9]*[,])?[0-9]+[ \t]+[+-]?([0-9]*[,])?[0-9]+$"),
        ],
    },
    "reflectance.mon": {
        "columns": (0, 1),
        "method": "reflectance",
        "radix_point": "\\.",
        "field_delimiter": " +",
        "split_indices": (14, -4),
        "line_matchers": [re.compile("^//Монохроматор: результаты регистрации$")],
    },
    "reflectance.csv": {
        "columns": (0, 1),
        "method": "reflectance",
        "radix_point": "\\,",
        "field_delimiter": "; ",
        "split_indices": (1,),
        "line_matchers": [
            re.compile("^nm; ((%R)|A)$"),
            re.compile("[+-]?([0-9]*[,])?[0-9]+; [+-]?([0-9]*[,])?[0-9]+"),
            re.compile("[+-]?([0-9]*[,])?[0-9]+; [+-]?([0-9]*[,])?[0-9]+"),
        ],
    },
    "raman.txt": {
        "columns": (0, 1),
        "method": "raman",
        "radix_point": "\\.",
        "field_delimiter": "\t",
        "split_indices": (0,),
        "line_matchers": [
            re.compile("^[+-]?([0-9]*[.])?[0-9]+[\t][+-]?([0-9]*[.])?[0-9]+$")
        ],
    },
    "raman2.txt": {
        "columns": (0, 4),
        "method": "raman2",
        "radix_point": "\\.",
        "field_delimiter": "\t",
        "split_indices": (1,),
        "line_matchers": [
            re.compile(
                "^wave number\tDark Subtracted\tdark data\tRaw data\tDark Subtracted Pull baseline$"
            )
        ],
    },
    "ftir.dpt": {
        "columns": (0, 1),
        "method": "ftir",
        "radix_point": "\\.",
        "field_delimiter": ",",
        "split_indices": (0,),
        "line_matchers": [
            re.compile("^[+-]?([0-9]*[.])?[0-9]+[,][+-]?([0-9]*[.])?[0-9]+$")
        ],
    },
    "xrd.txt": {
        "columns": (0, 1),
        "method": "xrd",
        "radix_point": "\\.",
        "field_delimiter": " +",
        "split_indices": (0,),
        "line_matchers": [
            re.compile("^[+-]?([0-9]*[.])?[0-9]+ +[0-9]+$"),
            re.compile("^[+-]?([0-9]*[.])?[0-9]+ +[0-9]+$"),
            re.compile("^[+-]?([0-9]*[.])?[0-9]+ +[0-9]+$"),
        ],
    },
    "xrf.txt": {
        "columns": (0, 1),
        "method": "xrf",
        "radix_point": "\\.",
        "field_delimiter": "[\t][ ]+",
        "split_indices": (0,),
        "line_matchers": [
            re.compile("^[+-]?([0-9]*[.])?[0-9]+\t +[+-]?([0-9]*[.])?[0-9]+$"),
            re.compile("^[+-]?([0-9]*[.])?[0-9]+\t +[+-]?([0-9]*[.])?[0-9]+$"),
            re.compile("^[+-]?([0-9]*[.])?[0-9]+\t +[+-]?([0-9]*[.])?[0-9]+$"),
        ],
    },
    "xrf.dat": {
        "columns": (0, 1),
        "method": "xrf_single_column",
        "radix_point": "(?!)",
        "field_delimiter": "(?!)",
        "split_indices": (1,),
        "line_matchers": [
            re.compile("^[+-]?([0-9]*[.])?[0-9]+ [+-]?([0-9]*[.])?[0-9]+$"),
            re.compile("^[0-9]+$"),
            re.compile("^[0-9]+$"),
        ],
    },
    "xrd.xy": {
        "columns": (0, 1),
        "method": "xrd",
        "radix_point": "\\.",
        "field_delimiter": " +",
        "split_indices": (0,),
        "line_matchers": [
            re.compile("^[+-]?([0-9]*[.])?[0-9]+ [+-]?([0-9]*[.])?[0-9]+$"),
            re.compile("^[+-]?([0-9]*[.])?[0-9]+ [+-]?([0-9]*[.])?[0-9]+$"),
            re.compile("^[+-]?([0-9]*[.])?[0-9]+ [+-]?([0-9]*[.])?[0-9]+$"),
        ],
    },
    "thz.txt": {
        "columns": (0, 1),
        "method": "thz",
        "radix_point": "\\,",
        "field_delimiter": "\t",
        "split_indices": (0,),
        "line_matchers": [
            re.compile("^[+-]?([0-9]*[,])?[0-9]+\t[+-]?([0-9]*[,])?[0-9]+$"),
            re.compile("^[+-]?([0-9]*[,])?[0-9]+\t[+-]?([0-9]*[,])?[0-9]+$"),
            re.compile("^[+-]?([0-9]*[,])?[0-9]+\t[+-]?([0-9]*[,])?[0-9]+$"),
        ],
    },
    "thz2.txt": {
        "columns": (0, 1),
        "method": "thz2",
        "radix_point": "\\,",
        "field_delimiter": " ",
        "split_indices": (0,),
        "line_matchers": [
            re.compile("^[+-]?([0-9]*[,])?[0-9]+ [+-]?([0-9]*[,])?[0-9]+$"),
            re.compile("^[+-]?([0-9]*[,])?[0-9]+ [+-]?([0-9]*[,])?[0-9]+$"),
            re.compile("^[+-]?([0-9]*[,])?[0-9]+ [+-]?([0-9]*[,])?[0-9]+$"),
        ],
    },
    "xrf2.txt": {
        "columns": (0, 1),
        "method": "xrf",
        "radix_point": "\\.",
        "field_delimiter": ", +",
        "split_indices": (0,),
        "line_matchers": [
            re.compile("^[+-]?([0-9]*[.])?[0-9]+, +[0-9]+$"),
            re.compile("^[+-]?([0-9]*[.])?[0-9]+, +[0-9]+$"),
            re.compile("^[+-]?([0-9]*[.])?[0-9]+, +[0-9]+$"),
        ],
    },
}
