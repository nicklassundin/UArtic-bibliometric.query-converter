import elsapy
import os
import json
import pandas as pd
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch
import re


import pybliometrics

from pybliometrics.scopus import AbstractRetrieval

from pybliometrics.scival import init, PublicationLookup, TopicLookupMetrics


class Scopus:
    def __init__(self, query):
        self.query = query
        # check if ./config exists
        if not os.path.exists("./config"):
            os.makedirs("./config")
            self.__addAPIKey()
        elif not os.path.exists("./config/scopus.json"):
            self.__addAPIKey()
        con_file = open('./config/scopus.json')
        self.config = json.load(con_file)
        con_file.close()
        ## Initialize client
        self.client = ElsClient(self.config['apikey'])
        self.client.inst_token = self.config['insttoken']


        pybliometrics.init(None, [self.config['apikey']], [self.config['insttoken']])

    def __addAPIKey(self):
        apikey = input("Put in APIKEY")
        insttoken = input("Insttoken (optional, press enter to skip)")
        # save to config file
        data = { 'apikey': apikey }
        if insttoken != "":
            data['insttoken'] = insttoken
        with open("./config/scopus.json", "w") as f:
            json.dump(str(data), f)

    def convertEID(self, eid: str):
        m = re.fullmatch(r'(?:SCOPUS_ID:)?(?:2-s2\.0-)?(\d+)', eid.strip())
        return m.group(1)
    
    def getScopus(self, eid: str):
        eid = self.convertEID(eid)
        ab = AbstractRetrieval(eid, view = 'FULL')
        return ab
    def getSciVal(self, eid: str):
        eid = self.convertEID(eid)
        pub = PublicationLookup(eid)
        tm = TopicLookupMetrics(str(pub.topic_id))
        df = pd.DataFrame(tm.ScholarlyOutput);
        # replace entity in column by topic 
        df.columns = [col.replace('entity', 'topic') for col in df.columns]
        # keep ony topic_id and topic_name
        df = df[['topic_id', 'topic_name']]

        tm_c = TopicLookupMetrics(str(pub.topic_cluster_id))
        # replace entity in column by topic_cluster
        df_c = pd.DataFrame(tm_c.ScholarlyOutput);
        df_c.columns = [col.replace('entity', 'topic_cluster') for col in df_c.columns]
        df_c = df_c[['topic_cluster_id', 'topic_cluster_name']]

        # col bind
        df = pd.concat([df, df_c], axis=1)

        df['title'] = pub.title
        df['doi'] = pub.doi
        df['topic_id'] = pub.topic_id
        return df

    def search(self):
        EID = '2-s2.0-85065577450'
        print(EID)
        # meta = self.getTopic(EID)
        meta = self.getSciVal(EID)

        print(meta)
        # prent all attributes names
        attributes = []
        for attr in dir(meta):
            attributes.append(attr)

        return None

        print(meta.subject_areas)
        search = ElsSearch(self.query, 'scopus')
        try: 
            # answer = search.execute(self.client, get_all=True)
            search.execute(self.client, 
                           get_all=False,
                           # view='STANDARD')
                           view='COMPLETE')
            # TODO get field needed
            results = search.results
            

        except Exception as e:
            print("Error:", str(e))
            with open("output/scopus.error.json", "w") as f:
                json.dump(str(e), f)

        df = pd.DataFrame(results)
            
        print(df['affiliation'][0][0])
        print(df['affiliation'][0][0]['affilname'])
        EID = df['eid'][0]
        print(EID)
        meta = self.getTopic(EID)
        print(meta.subject_areas)

        if 'affiliation' in df.columns:
            df['Institution'] = df['affiliation'].apply(lambda x: pd.Series(x[0]['affilname']))
            df['City'] = df['affiliation'].apply(lambda x: pd.Series(x[0]['affiliation-city'])) 
            df['Country'] = df['affiliation'].apply(lambda x: pd.Series(x[0]['affiliation-country']))


        df.to_excel("output/scopus.xlsx", index=False)

