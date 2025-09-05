import os
import json
from pathlib import Path
from openpyxl import load_workbook
import pandas as pd
import regex as re
import sys

arguments = os.sys.argv

# debug
debug = False
if ('-d' in arguments) or ('--debug' in arguments):
    debug = True

SAMPLE_SIZE = 10


if not os.path.exists("./output"):
    print("Creating output directory...")
    os.makedirs("./output")

## Find Query String
# read all files in descriptions
files = os.listdir("descriptions")
# get file containing 'ARCTIC_TERMS*'
file = [f for f in files if f.startswith("ARCTIC_TERMS")][0]

# read xlsx file no header
print("Reading file:", file)
wb = load_workbook(filename="descriptions/" + file, read_only=True)
sheet = wb.worksheets[3]
# convert to dataframe
df = pd.DataFrame(sheet.values)
# remove empty rows
df = df.dropna(how='all')


print(df)
strings = {}
RAW_QUERY = ''
for i in range(len(df)):
    RAW_QUERY = df.iloc[i,0]
    if not RAW_QUERY or not isinstance(RAW_QUERY, str):
        continue
    if df.iloc[i,3] == 'Merge' or df.iloc[i,3] == 'Final':    
        # print(RAW_QUERY[0:100])
        # for keys in strings.keys():
        # reverse order
        for key in sorted(strings.keys(), key=len, reverse=True):
            # print(key)
            RAW_QUERY = RAW_QUERY.replace(key, strings[key])
        # print(RAW_QUERY[0:100])
    key = df.iloc[i,1]
    if key == None or not isinstance(key, str):
        continue
    strings[key] = RAW_QUERY


from src.elsapy import Scopus
scopus = Scopus(RAW_QUERY)
scopus.search()
