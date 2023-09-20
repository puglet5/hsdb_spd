from typing import Tuple, TypedDict


class Filetype(TypedDict):
    line_delimiter: str
    decimal_delimiter: str
    split_indices: Tuple[int,] | Tuple[int, int]
    line_matchers: list[str]


filetypes: dict[str, Filetype] = {
    "libs.spectable": {
        "decimal_delimiter": "\\,",
        "line_delimiter": "\t",
        "split_indices": (2,),
        "line_matchers": [
            "^Wavelenght[ \t]+Spectrum$",
            "^Integration delay[ \t]+[+-]?([0-9]*[,])?[0-9]+$",
            "^[+-]?([0-9]*[,])?[0-9]+\t[+-]?([0-9]*[,])?[0-9]+$",
        ],
    },
    "libs.spec": {
        "decimal_delimiter": "\\,",
        "line_delimiter": "\t",
        "split_indices": (2,),
        "line_matchers": [
            "^[0-9]+$",
            "^[0-9]+$",
            "^[+-]?([0-9]*[,])?[0-9]+[ \t]+[+-]?([0-9]*[,])?[0-9]+$",
        ],
    },
    "reflectance.mon": {
        "decimal_delimiter": "\\.",
        "line_delimiter": " +",
        "split_indices": (14, -4),
        "line_matchers": ["^//Монохроматор: результаты регистрации$"],
    },
    "reflectance.csv": {
        "decimal_delimiter": "\\,",
        "line_delimiter": "; ",
        "split_indices": (1,),
        "line_matchers": [
            "^nm; ((%R)|A)$",
            "[+-]?([0-9]*[,])?[0-9]+; [+-]?([0-9]*[,])?[0-9]+",
            "[+-]?([0-9]*[,])?[0-9]+; [+-]?([0-9]*[,])?[0-9]+",
        ],
    },
    "raman.txt": {
        "decimal_delimiter": "\\.",
        "line_delimiter": "\t",
        "split_indices": (0,),
        "line_matchers": ["^[+-]?([0-9]*[.])?[0-9]+[\t][+-]?([0-9]*[.])?[0-9]+$"],
    },
    "ftir.dpt": {
        "decimal_delimiter": "\\.",
        "line_delimiter": ",",
        "split_indices": (0,),
        "line_matchers": ["^[+-]?([0-9]*[.])?[0-9]+[,][+-]?([0-9]*[.])?[0-9]+$"],
    },
    "xrd.txt": {
        "decimal_delimiter": "\\.",
        "line_delimiter": " +",
        "split_indices": (0,),
        "line_matchers": [
            "^[+-]?([0-9]*[.])?[0-9]+ +[0-9]+$",
            "^[+-]?([0-9]*[.])?[0-9]+ +[0-9]+$",
            "^[+-]?([0-9]*[.])?[0-9]+ +[0-9]+$",
        ],
    },
    "xrf.txt": {
        "decimal_delimiter": "\\.",
        "line_delimiter": "[\t][ ]+",
        "split_indices": (0,),
        "line_matchers": [
            "^[+-]?([0-9]*[.])?[0-9]+\t +[+-]?([0-9]*[.])?[0-9]+$",
            "^[+-]?([0-9]*[.])?[0-9]+\t +[+-]?([0-9]*[.])?[0-9]+$",
            "^[+-]?([0-9]*[.])?[0-9]+\t +[+-]?([0-9]*[.])?[0-9]+$",
        ],
    },
    "xrf.dat": {
        "decimal_delimiter": "(?!)",
        "line_delimiter": "(?!)",
        "split_indices": (1,),
        "line_matchers": [
            "^[+-]?([0-9]*[.])?[0-9]+ [+-]?([0-9]*[.])?[0-9]+$",
            "^[0-9]+$",
            "^[0-9]+$",
        ],
    },
    "xrd.xy": {
        "decimal_delimiter": "\\.",
        "line_delimiter": " +",
        "split_indices": (0,),
        "line_matchers": [
            "^[+-]?([0-9]*[.])?[0-9]+ [+-]?([0-9]*[.])?[0-9]+$",
            "^[+-]?([0-9]*[.])?[0-9]+ [+-]?([0-9]*[.])?[0-9]+$",
            "^[+-]?([0-9]*[.])?[0-9]+ [+-]?([0-9]*[.])?[0-9]+$",
        ],
    },
    "thz.txt": {
        "decimal_delimiter": "\\,",
        "line_delimiter": "\t",
        "split_indices": (0,),
        "line_matchers": [
            "^[+-]?([0-9]*[,])?[0-9]+\t[+-]?([0-9]*[,])?[0-9]+$",
            "^[+-]?([0-9]*[,])?[0-9]+\t[+-]?([0-9]*[,])?[0-9]+$",
            "^[+-]?([0-9]*[,])?[0-9]+\t[+-]?([0-9]*[,])?[0-9]+$",
        ],
    },
}
