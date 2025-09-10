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

# topics = Topics().get()
# works = Works().filter(institutions={"country_code": "se"}).paginate(per_page=100)
# works = Works().filter(
        # institutions={"is_global_north": True}).paginate()

# authors = Authors().search_filter(display_name="Leif Karlsson").get()
# workToJson(authors, "leif")

# authors = Authors().search_filter(display_name="Keith Larson").get()
# workToJson(authors, "keith")

# institutions = Institutions().filter(country_code="se").paginate(per_page=100)
# institutions = Institutions().paginate(per_page=100)

# complete_institutions = []
# # progress bar
# for institution in tqdm.tqdm(institutions):
#     # merge institution with complete_institutions
#     complete_institutions += institution

# workToJson(complete_institutions, "institutions")


# Scopus
# import pybliometrics
# from pybliometrics.scopus import ScopusSearch
# pybliometrics.init()
# s = ScopusSearch(RAW_TEST_QUERY, view="STANDARD", refresh=True)
# print(len(s.results))
# print(s.results[0].title) 
# print(s.results[0].author_names) 

from dataclasses import dataclass
from typing import List, Optional

from src.lexer import lexer, Tok, AST, Ident, String, Number, Not, And, Or, Cmp, Call
# A recursive descent parser for the query language
class Parser:
    def __init__(self, tokens):
        self.tokens = list(tokens) + [Tok('EOF', '', len(tokens))]
        self.pos = 0
    def peek(self):
        return self.tokens[self.pos]

    def match(self, *kinds) -> Optional[Tok]:
        t = self.peek()
        if t and t.kind in kinds:
            self.pos += 1
            return t
        return None
    
    def expect(self, *kinds) -> Tok:
        t = self.match(*kinds)
        if not t:
            raise SyntaxError(f"expected one of {kinds}, got {self.peek().kind} at {self.peek().pos}")
        return t

    def parse(self):
        node = self.parse_or()
        if self.peek().kind != 'EOF':
            print("test")
            print(self.tokens[self.pos-2:self.pos])
            raise SyntaxError(f"Unexpected token {self.peek().kind} at {self.peek().pos}")
        return node
    
    def parse_or(self):
        node = self.parse_and()
        while self.match('OR'):
            right = self.parse_and()
            node = Or(node, right)
        return node

    def parse_and(self):
        node = self.parse_not()
        while self.match('AND'):
            right = self.parse_not()
            node = And(node, right)
        return node

    def parse_not(self):
        if self.match('NOT'):
            return Not(self.parse_not())
        return self.parse_primary()

    def parse_primary(self) -> AST:
        if self.match('LPAREN'):
            node = self.parse_or()
            self.expect('RPAREN')
            return node

        t = self.peek()
        if t and t.kind == 'IDENT':
            name = t.value;
            self.pos += 1
            if self.match('LPAREN'):
                arg = self.parse_or()
                self.expect('RPAREN')
                return Call(name, arg)

            op_tok = self.match('OP')
            if op_tok:
                num = self.expect('NUMBER')
                return Cmp(name, op_tok.value, Number(int(num.value)))

            return Ident(name)

        if self.match('STRING'):
            return String(self.tokens[self.pos - 1].value)
        if self.match('NUMBER'):
            return Number(int(self.tokens[self.pos - 1].value))

        t = self.peek()
        raise SyntaxError(f"Unexpected token {t.kind} at {t.pos}")

# Top-level function to parse a query string into an AST 
def parse_query(query: str) -> AST:
    toks = list(lexer(query))
    # for t in toks:
        # print(t)
    return Parser(toks).parse()

# A function to pretty-print the AST
def dump(ast: AST, indent=0):
    pad = '  ' * indent
    if isinstance(ast, (Ident, String, Number)):
        if isinstance(ast, Ident):  print(f"{pad}Ident({ast.name})")
        if isinstance(ast, String): print(f'{pad}String("{ast.value}")')
        if isinstance(ast, Number): print(f"{pad}Number({ast.value})")
    elif isinstance(ast, Not):
        print(f"{pad}Not("); dump(ast.expr, indent+1); print(f"{pad})")
    elif isinstance(ast, And):
        print(f"{pad}And("); dump(ast.left, indent+1); dump(ast.right, indent+1); print(f"{pad})")
    elif isinstance(ast, Or):
        print(f"{pad}Or("); dump(ast.left, indent+1); dump(ast.right, indent+1); print(f"{pad})")
    elif isinstance(ast, Cmp):
        print(f"{pad}Cmp(field={ast.field!r}, op={ast.op!r}, value={ast.value.value})")
    elif isinstance(ast, Call):
        print(f"{pad}Call(func={ast.func!r},")
        dump(ast.arg, indent+1)
        print(f"{pad})")
    else:
        print(f"{pad}{ast}")


# A function to convert the AST to a LaTeX-like math representation
def to_math(ast) -> str:
        if isinstance(ast, Ident):
            return ast.name
        if isinstance(ast, String):
            return f'"{ast.value}"'
        if isinstance(ast, Number):
            return str(ast.value)
        if isinstance(ast, Not):
            return r"\lnot " + to_math(ast.expr)
        if isinstance(ast, And):
            return f"( {to_math(ast.left)} \\land {to_math(ast.right)} )"
        if isinstance(ast, Or):
            return f"( {to_math(ast.left)} \\lor {to_math(ast.right)} )"
        if isinstance(ast, Cmp):
            return f"{ast.field} {ast.op} {to_math(ast.value)}"
        if isinstance(ast, Call):
            return f"\\text{{{ast.func}}}( {to_math(ast.arg)} )"
        return "?"



def compose(g, f):
    def composed(x):
        return g(f(x))
    return composed

# lazy composition 
def lazy_compose(g, f):
    def composed(x):
        return g(f(x))
    return composed


# TODO
# Refactor to generalized mapTo with structure OpenAlex or others convertions
def mapToOpenAlex(ast: AST, f: Callable[[], Works]) -> [Callable[[], Works]]:
    if isinstance(f, list):
        results = []
        for g in f:
            g = mapToOpenAlex(ast, g)
            if isinstance(g, list):
                results += g
            else:
                results += [g]
        return results
    if isinstance(ast, And):
        
        g = mapToOpenAlex(ast.left, f)
        g = mapToOpenAlex(ast.right, g)
        return g
    elif isinstance(ast, Or):
        left = mapToOpenAlex(ast.left, f)
        right = mapToOpenAlex(ast.right, f)
        if not isinstance(left, list):
            left = [left]
        if not isinstance(right, list):
            right = [right]
        return left + right
    elif isinstance(ast, Not):
        # only support NOT DOCTYPE ( er )
        if isinstance(ast.expr, Call) and ast.expr.func == 'DOCTYPE':
            if isinstance(ast.expr.arg, Ident):
                if ast.expr.arg.name.lower() == 'er':
                    def g(x):
                        if not x.__dict__.get('params', {}):
                            return x.filter(type="!erratum")
                        elif "!erratum" not in x.__dict__.get('params', {}).get('filter', {}).get('type', []):
                            return x.filter(type="!erratum")
                    return compose(g, f)
        return f
    elif isinstance(ast, Call):
        # for TITLE-ABS
        if ast.func == 'TITLE-ABS':
            if isinstance(ast.arg, Or):
                terms = []
                def collect_terms(node):
                    if isinstance(node, Or):
                        collect_terms(node.left)
                        collect_terms(node.right)
                    elif isinstance(node, Ident):
                        terms.append(node.name)
                    elif isinstance(node, String):
                        terms.append(node.value)
                collect_terms(ast.arg)
                terms = [quote(g, safe="") for g in terms]
                # search_terms = "|".join(terms)
                work = []
                # split into 50 terms each
                chunk_size = 50
                terms = [terms[i:i + chunk_size] for i in range(0, len(terms), chunk_size)]
                # for each chunk, create a separate function
                for chunk in terms:
                # for i in range(len(terms)):
                    t = "|".join(chunk)
                    def g(x):
                        return x.search_filter(title = t)
                    work.append(compose(g, f))
                # def g(x):
                    # return x.search_filter(title=search_terms)
                # return compose(g, f)
                return work
            elif isinstance(ast.arg, Ident):
                def g(x):
                    return x.search_filter(title=ast.arg.name)
                return compose(g, f)
            elif isinstance(ast.arg, String):
                def g(x):
                    return x.search_filter(title=ast.arg.value)
                return compose(g, f)
        elif ast.func == 'AUTHKEY':
            if isinstance(ast.arg, Or):
                terms = []
                def collect_terms(node):
                    if isinstance(node, Or):
                        collect_terms(node.left)
                        collect_terms(node.right)
                    elif isinstance(node, Ident):
                        terms.append(node.name)
                    elif isinstance(node, String):
                        terms.append(node.value)
                collect_terms(ast.arg)
                
                # reduce multiple " " spaces after
                #' For safe search terms
                # terms = [quote(g, safe="") for g in terms]
                terms = [squash_spaces(g) for g in terms]
                terms = [g.replace("'", "%27").replace(" ", "%20") for g in terms]
                # TODO test if , is needed to be removed
                terms = [g.replace(",", "") for g in terms]
                # search_terms = "|".join(terms)
                work = []
                chunk_size = 50
                terms = [terms[i:i + chunk_size] for i in range(0, len(terms), chunk_size)]
                # for each chunk, create a separate function
                for chunk in terms:
                # for i in range(len(terms)):
                    t = "|".join(chunk)
                    def g(x):
                        return x.search_filter(display_name = t)
                    work.append(compose(g, f))
                return work 
            elif isinstance(ast.arg, Ident):
                def g(x):
                    return x.search_filter(display_name = ast.arg.name)
                return compose(g, f)
            elif isinstance(ast.arg, String):
                def g(x):
                    return x.search_filter(display_name = ast.arg.value)
                return compose(g, f)
        elif ast.func == 'DOCTYPE':
            if isinstance(ast.arg, Ident):
                if ast.arg.name.lower() == 'er':
                    def g(x):
                        if not x.__dict__.get('params', {}):
                            return x.filter(type="erratum")
                        elif "erratum" not in work.__dict__.get('params', {}).get('filter', {}).get('type', []):
                            return x.filter(type="erratum")
                    return compose(g, f)

    if isinstance(ast, Cmp):
        if ast.field == 'PUBYEAR':
            if ast.op in ('>', '>=', '<', '<=') and isinstance(ast.value, Number):
                if ast.op == '>':
                    def g(x):
                        if not x.__dict__.get('params', {}):
                            return x.filter(from_publication_date=f"{ast.value.value + 1}-01-01")
                        else:
                            filters = x.__dict__.get("params", {}).get("filter", {})
                            from_date = filters.get("from_publication_date", None)
                            new_date = f"{ast.value.value + 1}-01-01"
                            if not from_date or from_date < new_date:
                                x = x.filter(from_publication_date=new_date) 
                            return x
                    return compose(g, f)
                elif ast.op == '<':
                    def g(x):
                        if not x.__dict__.get('params', {}):
                            return x.filter(to_publication_date=f"{ast.value.value - 1}-12-31")
                        else:
                            filters = x.__dict__.get("params", {}).get("filter", {})
                            to_date = filters.get("to_publication_date", None)
                            new_date = f"{ast.value.value - 1}-12-31"
                            if not to_date or to_date > new_date:
                                x = x.filter(to_publication_date=new_date) 
                            return x
                    return compose(g, f)

    return f


class OpenAlex:
    def __init__(self, query: str, debug: bool = False):
        self.query = query
        self.debug = debug
        self.ast = parse_query(self.query)
    def dump(self):
        dump(self.ast)
    def produceMarkdown(self):
        markdown = to_math(self.ast)
        with open("output/query.md", "w", encoding="utf-8") as f:
            f.write(markdown)
    def mapToOpenAlex(self):
        works = mapToOpenAlex(self.ast, lambda x: x)
        return works;
    def process(self, works):
        data = {}
        with open("output/query.json", "w") as f:
            for i, work in enumerate(works):
                print(works[i])
                works[i] = work(Works())
                data[i] = works[i].__dict__
            json.dump(data, f, indent=4)
        return works
    def execute(self, works):
        results = []
        bar = tqdm.tqdm(total=len(works), unit="queries", desc="Fetching works")
        for w in works:
            bar.n += 1
            bar.refresh()
            try:
                # for page in w.paginate(per_page=200):
                if self.debug:
                    bar2 = tqdm.tqdm(total=SAMPLE_SIZE, unit="works", desc="Fetching pages", leave=False)
                    page = w.sample(SAMPLE_SIZE, seed=535).get()
                    bar2.n += 1;
                    bar2.refresh()
                    results += page
                else:
                    bar2 = tqdm.tqdm(total=w.count(), unit="works", desc="Fetching pages", leave=False)
                    for page in w.paginate(per_page=200):
                        bar2.n += len(page)
                        bar2.refresh()
                        results += page
                        # results.expand(page)
                        # save periodically (e.g. every 100 works)
            except Exception as e:
                print("Error occurred:", e)
                # save whatever you got so far
                with open("output/error.json", "w") as f:
                    # dump e as string
                    json.dump(str(e), f)

        # map over results and keep entry['ids']
        results = [entry['ids'] for entry in results]

        with open("output/backup.json", "w") as f:
            print("Save Result")
            json.dump(results, f)

        # save as xlsx file
        df = pd.DataFrame(results)
        df.to_excel("output/output.xlsx", index=False)

    def rundown(self):
        self.dump()
        self.produceMarkdown()
        works = self.mapToOpenAlex()
        works = self.process(works)
        self.execute(works)


