import os
import json
import numpy as np
from elasticsearch import Elasticsearch
from gensim.models.word2vec import Word2Vec
from compass_embeddings.create_compass_data import preprocess

query_embeddings = Word2Vec.load(
    os.path.join("compass_embeddings", "model", "query_tweets.model")
)
user_embeddings = {}


def query_search(query, count_result, user, topic, method):
    client = Elasticsearch()

    # termini che possono comparire
    # mettiamo quelli del profilo utente
    # nel caso ci siano aumenta lo score del documento
    should = []

    # i termini che devono comparire
    # mettiamo il topic nel caso sia scelto dall'utente
    # per ricercare solo sui tweet di quel topic
    must = []
    str_profile = []
    must.append({"query_string": {"query": query, "default_field": "text"}})

    if user != "None":
        if method == "bow":
            with open("./user_profile/data/bow.json") as jsonfile:
                data = json.load(jsonfile)

            for bow in data:
                if list(bow.keys())[0] == user:
                    # should.extend([{"term": {"text": str(word)}} for word in bow[user]])
                    str_profile = " ".join(str(word) for word in bow[user])
                    should.append({"match": {"text": str_profile}})
        elif method == "embeddings_mean" or method == "embeddings":
            user_embedding = None
            try:
                user_embedding = user_embeddings[user]
            except KeyError:
                user_embeddings[user] = Word2Vec.load(
                    os.path.join(
                        "compass_embeddings", "model", "@" + user + "_tweets.model"
                    )
                )
                user_embedding = user_embeddings[user]

            preprocessed_query = preprocess([query])
            vectors = []
            shoulds = []
            for token in preprocessed_query.split():
                try:
                    vectors.append(query_embeddings.wv.get_vector(token))
                except KeyError:
                    print("Token " + token + " not found in query embeddings")
            if method == "embeddings_mean" and vectors != []:
                mean_vector = np.mean(vectors, axis=0)
                shoulds = [
                    word
                    for word, sim in user_embedding.wv.most_similar(
                        [mean_vector], topn=10
                    )
                ]
                should.append({"match": {"text": " ".join(shoulds)}})
            elif method == "embeddings" and vectors != []:
                for vector in vectors:
                    shoulds.extend(
                        [
                            (word, sim)
                            for word, sim in user_embedding.wv.most_similar(
                                [vector], topn=10
                            )
                        ]
                    )
                shoulds = sorted(shoulds, key=lambda x: x[1], reverse=True)[:10]
                shoulds = [word for word, sim in shoulds]
                should.append({"match": {"text": " ".join(list(set(shoulds)))}})

    if topic != "None":
        must.append({"term": {"topic": topic}})
        # topic_filter = {"filter":{"term": {"topic": topic}}}
    print("SHOULD", should)
    q = {"must": must, "should": should}
    body = {"size": count_result, "query": {"function_score": {"query": {"bool": q}}}}
    res = client.search(index="index_twitter", body=body)
    res = res["hits"]["hits"]
    # print('Ho trovato: ', len(res), ' tweet')

    return res
