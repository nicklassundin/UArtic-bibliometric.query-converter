import pyalex
import hashlib
import tqdm
import os
from pathlib import Path
from pyalex import config
from pyalex import Works, Authors, Sources, Institutions, Topics, Publishers, Funders
import json
import pandas as pd
from urllib.parse import quote
from typing import Callable

pyalex.config.email = "p4c@hotmail.com"

import re
def squash_spaces(s: str) -> str:
    s = s.replace("\u00A0", " ")
    return re.sub(r"\s+", " ", s).strip()

SAMPLE_SIZE = 10


from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Tok:
    kind: str
    value: str
    pos: int

KEYWORDS = {'AND', 'OR', 'NOT', 'W/3'}

@dataclass
class AST: ...
@dataclass
class Ident(AST): name: str
@dataclass
class String(AST): value: str
@dataclass
class Number(AST): value: int
@dataclass
class Not(AST): expr: AST
@dataclass
class And(AST): left: AST; right: AST
@dataclass
class Or(AST): left: AST; right: AST
@dataclass
class Cmp(AST): field: str; op: str; value: AST
@dataclass
class Call(AST): func: str; arg: AST

import tqdm
from copy import deepcopy

# A simple lexer for the query language
# yields tokens one by one
def lexer(string: str):
    i, n = 0, len(string)
    
    bar = tqdm.tqdm(total=n, unit="chars", desc="Lexing")

    while i < n:
        bar.n = i
        # add text
        bar.set_postfix({'char': string[i], 'surround': string[i-5:i+5]})
        bar.refresh()
        c = string[i]
        if c.isspace():
            i += 1
            continue
       
        if c == '(':
            yield Tok('LPAREN', c, i)
            i += 1
            continue
        if c == ')':
            yield Tok('RPAREN', c, i)
            i += 1
            continue

        # compare operators
        if c in '<>=':
            j = i + 1
            if j < n and string[j] == '=' and c in '<>':
                yield Tok('OP', c + '=', i)
                i = j + 1
            yield Tok('OP', c, i)
            i += 1
            continue

        if c == '"':
            i0 = i;
            i += 1
            buffer = []
            while i < n:
                ch = string[i]
                bar.n = i
                bar.set_postfix({'char': ch, 'surround': string[i-5:i+5]})
                bar.refresh()
                if ch == '\\' and i + 1 < n:
                    buffer.append(string[i + 1])
                    i += 1
                    continue
                if ch == '"':
                    i += 1
                    break
                buffer.append(ch)
                i += 1
            yield Tok('STRING', ''.join(buffer), i0)
            continue

        if c.isdigit():
            i0 = i
            while i < n and string[i].isdigit():
                i += 1
            yield Tok('NUMBER', string[i0:i], i0)
            continue

        # Word
        if c.isalpha() or c == '_':
            i0 = i
            while i < n and (string[i].isalnum() or string[i] in "_-."):
                i += 1
            word = string[i0:i];
            U = word.upper()
            kind = U if U in KEYWORDS else 'IDENT'
            yield Tok(kind, U if kind in KEYWORDS else word, i0)
            continue

        # fallback
        yield Tok('CHAR', c, i); i += 1

