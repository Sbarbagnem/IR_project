import os
import json
import tweepy
import pandas as pd
from config import CONSUMER_KEY, CONSUMER_SECRET


def process_tweet(tweet, id, topic):
    """
		Create a tweet object with only important attribute
		list:
			id
			created_at
			text
			user
			country
			followers_count
			number_like
			number_retweet
			profile_image_url_https
            tweet_url
            topic
	"""
    temp_tweet = {}

    temp_tweet["id"] = id
    temp_tweet["tweet_id"] = tweet.id_str
    temp_tweet["created_at"] = tweet.created_at.isoformat()
    temp_tweet["text"] = tweet.full_text
    temp_tweet["name_user"] = tweet.user.name
    temp_tweet["followers_count"] = int(tweet.user.followers_count)
    temp_tweet["like"] = int(tweet.favorite_count)
    temp_tweet["retweet"] = int(tweet.retweet_count)
    temp_tweet["profile_image_url"] = tweet.user.profile_image_url_https
    temp_tweet[
        "tweet_url"
    ] = f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"
    if tweet.place is not None:
        temp_tweet["country"] = tweet.place.country_code
    else:
        temp_tweet["country"] = ""

    temp_tweet["topic"] = topic.split()[0]

    return temp_tweet


def read_tweet_pre_downladed(filepath):

    # read and return json with tweet yet downloaded
    with open(filepath) as json_file:
        data = json.load(json_file)

    return data


def crawl_tweet_for_topic(topic, id_tweet, sinceId):

    print("Inizio crawl per il topic: ", topic)

    searchQuery = topic

    # servono per tenere traccia del punto in cui si è arrivati
    if sinceId != {}:
        sinceId = str(sinceId)
    else:
        sinceId = "0"

    max_id = 0

    tweet_list = []
    tweetCount = 0
    id_tweet = id_tweet

    while tweetCount < MAX_TWEETS:
        try:
            if max_id <= 0:
                if sinceId == "0":
                    new_tweets = api.search(
                        q=searchQuery,
                        count=TWEET_FOR_QUERY,
                        tweet_mode="extended",
                        lang="en",
                        result_type="mixed",
                        include_entities=False,
                    )
                else:
                    new_tweets = api.search(
                        q=searchQuery,
                        count=TWEET_FOR_QUERY,
                        tweet_mode="extended",
                        lang="en",
                        result_type="mixed",
                        include_entities=False,
                        since_id=sinceId,
                    )
            else:
                if sinceId == "0":
                    new_tweets = api.search(
                        q=searchQuery,
                        count=TWEET_FOR_QUERY,
                        tweet_mode="extended",
                        lang="en",
                        result_type="mixed",
                        include_entities=False,
                        max_id=str(max_id - 1),
                    )
                else:
                    new_tweets = api.search(
                        q=searchQuery,
                        count=TWEET_FOR_QUERY,
                        tweet_mode="extended",
                        lang="en",
                        result_type="mixed",
                        include_entities=False,
                        max_id=str(max_id - 1),
                        since_id=sinceId,
                    )
            if not new_tweets:
                print("No more tweets found")
                break
            for tweet in new_tweets:
                tweet_list.append(process_tweet(tweet, id_tweet, topic))
                id_tweet = id_tweet + 1
                # json.dump(tweet_list, f, indent=3)
            tweetCount = tweetCount + len(new_tweets)
            max_id = new_tweets[-1].id

        except tweepy.TweepError as e:
            # Just exit if any error
            print("some error : " + str(e))
            break

    return id_tweet, tweet_list


def find_last_id(tweets):

    since_id = {}

    df = pd.DataFrame([tweet for tweet in tweets])
    df = df[["tweet_id", "created_at", "topic"]]

    df = df.sort_values("created_at").groupby("topic").last()
    max_id = max(df["tweet_id"].tolist())

    return max_id


if __name__ == "__main__":

    # Creating the authentication object
    auth = tweepy.AppAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    # Setting your access token and secret

    # Creating the API object while passing in auth information
    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

    MAX_TWEETS = 30000  # Some arbitrary large number
    TWEET_FOR_QUERY = 100  # this is the max the API permits
    FILE_TWEETS = os.path.join("data", "query", "query.json")

    # leggo se nel json sono già presenti dei tweet
    tweet_list = read_tweet_pre_downladed(FILE_TWEETS)

    print("Numero di tweet già salvati nel json: ", len(tweet_list))

    # se presenti dei tweet prendo ultimo id, in index serve id univoco
    if len(tweet_list) == 0:
        id_tweet = 1
        tweet_list = []
    else:
        id_tweet = tweet_list[len(tweet_list) - 1]["id"]
        since_id = find_last_id(tweets=tweet_list)

    topics = [
        "sport -filter:retweets",
        "music -filter:retweets",
        "cinema -filter:retweets",
        "technology -filter:retweets",
        "politics -filter:retweets",
        "economy -filter:retweets",
    ]

    # per ogni topic scarico MAX_TWEETS tweet e creo lista di oggetti tweet
    for topic in topics:
        print("Cerco tweets per il topic: ", topic)
        last_id, temp_list = crawl_tweet_for_topic(
            topic=topic, id_tweet=id_tweet, sinceId=since_id
        )
        id_tweet = last_id
        print("Scaricati ", len(temp_list), " per il topic ", topic)
        tweet_list.extend(temp_list)

    print("Ora nella lista ci sono: ", len(tweet_list), " tweets")

    with open(FILE_TWEETS, "w") as outfile:
        json.dump(tweet_list, outfile, indent=3)
