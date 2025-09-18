import elsapy
import os
import json
import pandas as pd
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch

class Scopus:
    def __init__(self, query):
        self.query = query
        # check if ./config exists
        if not os.path.exists("./config"):
            os.makedirs("./config")
            self.__addAPIKey()
        elif not os.path.exists("./config/scopus.json"):
            self.__addAPIKey()
        con_file = open("./config/scopus.json")
        config = json.load(con_file)
        con_file.close()
        ## Initialize client
        self.client = ElsClient(config['apikey'])
        self.client.inst_token = config['insttoken']

    def __addAPIKey(self):
        apikey = input("Put in APIKEY")
        insttoken = input("Insttoken (optional, press enter to skip)")
        # save to config file
        data = { 'apikey': apikey }
        if insttoken != "":
            data['insttoken'] = insttoken
        with open("./config/scopus.json", "w") as f:
            json.dump(str(data), f)

    def search(self):
        search = ElsSearch(self.query, 'scopus')
        try: 
            # answer = search.execute(self.client, get_all=True)
            search.execute(self.client, 
                           get_all=False,
                           view='STANDARD')
            # TODO get field needed
            df = pd.DataFrame(search.results)
            df.to_excel("scopus.xlsx", index=False)
        except Exception as e:
            print("Error:", str(e))
            with open("output/scopus.error.json", "w") as f:
                json.dump(str(e), f)


