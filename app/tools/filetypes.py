import re
from typing import Pattern, Tuple, TypedDict


class Filetype(TypedDict):
    field_delimiter: str
    radix_point: str
    split_indices: Tuple[int,] | Tuple[int, int]
    line_matchers: list[Pattern[str]]


filetypes: dict[str, Filetype] = {
    "libs.spectable": {
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
        "radix_point": "\\.",
        "field_delimiter": " +",
        "split_indices": (14, -4),
        "line_matchers": [re.compile("^//Монохроматор: результаты регистрации$")],
    },
    "reflectance.csv": {
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
        "radix_point": "\\.",
        "field_delimiter": "\t",
        "split_indices": (0,),
        "line_matchers": [
            re.compile("^[+-]?([0-9]*[.])?[0-9]+[\t][+-]?([0-9]*[.])?[0-9]+$")
        ],
    },
    "raman2.txt": {
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
        "radix_point": "\\.",
        "field_delimiter": ",",
        "split_indices": (0,),
        "line_matchers": [
            re.compile("^[+-]?([0-9]*[.])?[0-9]+[,][+-]?([0-9]*[.])?[0-9]+$")
        ],
    },
    "xrd.txt": {
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
