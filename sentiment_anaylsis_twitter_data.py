from tweepy import API
from tweepy import Cursor
import sys, errno
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
from textblob import TextBlob
import twitter_credentials
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import re
import tweepy
import functools
from tweepy import OAuthHandler
from tweepy import Stream
from tweepy.streaming import StreamListener
import socket
import json

import time
import json
from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark import StorageLevel
from functools import partial
import datetime

from pyspark.sql import *

import requests

# # # # TWITTER CLIENT # # # #
class TwitterClient():
    def __init__(self, twitter_user=None):
        self.auth = TwitterAuthenticator().authenticate_twitter_app()
        self.twitter_client = API(self.auth)
        self.twitter_user = twitter_user

    def get_twitter_client_api(self):
        return self.twitter_client

    def get_user_timeline_tweets(self, num_tweets):
        tweets = []
        for tweet in Cursor(self.twitter_client.user_timeline, id=self.twitter_user).items(num_tweets):
            tweets.append(tweet)
        return tweets

    def get_friend_list(self, num_friends):
        friend_list = []
        for friend in Cursor(self.twitter_client.friends, id=self.twitter_user).items(num_friends):
            friend_list.append(friend)
        return friend_list

    def get_home_timeline_tweets(self, num_tweets):
        home_timeline_tweets = []
        for tweet in Cursor(self.twitter_client.home_timeline, id=self.twitter_user).items(num_tweets):
            home_timeline_tweets.append(tweet)
        return home_timeline_tweets


# # # # TWITTER AUTHENTICATER # # # #
class TwitterAuthenticator():

    def authenticate_twitter_app(self):
        auth = OAuthHandler(twitter_credentials.CONSUMER_KEY, twitter_credentials.CONSUMER_SECRET)
        auth.set_access_token(twitter_credentials.ACCESS_TOKEN, twitter_credentials.ACCESS_TOKEN_SECRET)
        return auth


# # # # TWITTER STREAMER # # # #
class TwitterStreamer():
    """
    Class for streaming and processing live tweets.
    """
    def __init__(self):
        self.twitter_authentication = TwitterAuthenticator()

    def stream_tweets(self, c_socket, hash_tag_list):
        # This handles Twitter authentication and the connection to Twitter Streaming API
        listener = TwitterListener(c_socket)
        auth = self.twitter_authentication.authenticate_twitter_app()
        stream = Stream(auth, listener)

        # This line filter Twitter Streams to capture data by the keywords:
        stream.filter(track=hash_tag_list)


# # # # TWITTER STREAM LISTENER # # # #
class TwitterListener(StreamListener):
    """
    This is a basic listener that just prints received tweets to stdout.
    """
    def __init__(self, c_socket):
        self.client_socket = c_socket

    def on_data(self, data):
        try:
            msg = json.loads(data)
            str_msg = str(msg['text'].encode('utf-8'))
            print(str_msg)
            self.client_socket.send(msg['text'].encode('utf-8'))
            return True
        except BaseException as e:
            print("Error on_data: %s" % str(e))
            return True
        except KeyboardInterrupt:
            print("It's ok")
            return True
        except IOError as e:
            if e.errno == errno.EPIPE:
                print("Pipe Eror")
            return True


    def on_error(self, status):
        print(status)
        return True


class TweetAnalyzer:
    """
    Functionality for analyzing and categorizing content from tweets.
    """
    def clean_tweet(self, tweet):
        return ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", tweet).split())

    def analyze_sentiment(self, tweet):
        analysis = TextBlob(self.clean_tweet(tweet))

        if analysis.sentiment.polarity > 0:
            return 1
        elif analysis.sentiment.polarity == 0:
            return 0
        else:
            return -1

    def tweets_to_data_frame(tweets):
        df = pd.DataFrame(data=[tweet.text for tweet in tweets], columns=['tweets'])

        df['id'] = np.array([tweet.id for tweet in tweets])
        df['len'] = np.array([len(tweet.text) for tweet in tweets])
        df['date'] = np.array([tweet.created_at for tweet in tweets])
        df['source'] = np.array([tweet.source for tweet in tweets])
        df['likes'] = np.array([tweet.favorite_count for tweet in tweets])
        df['retweets'] = np.array([tweet.retweet_count for tweet in tweets])

        return df


def get_sentiment_multiplide_by_retweet(tweet):
    return int(tweet.retweet_count)*int(tweet_analyzer.analyze_sentiment(tweet.text))


def get_values_by_hashtag(hash_tag):
    # get tweets for 1 hash tag starting from date
    rdd = sc.parallelize(api.search(q=hash_tag, from_date=startDate))

    # make rdd list of tuples (text of tweet, sentiment multiplied by re tweet
    # and getting read of duplicate tweets (bots)
    rdd_dictionary_set = rdd.map(lambda x: (x.text, get_sentiment_multiplide_by_retweet(x))) \
        .reduceByKey(lambda a, b: a)

    # make rdd dictionary with Set of key's
    rdd_values = rdd_dictionary_set.values()

    sum_of_values = 0
    # you can not activate reduce on empty rdd
    if not rdd_values.isEmpty():
        # get sum of all sentiment multiplied by re tweet values
        sum_of_values = rdd_values.reduce(lambda x, y: x + y)
        print(hash_tag, " ", sum_of_values)

    return sum_of_values


if __name__ == '__main__':
    # for displaying all columns of data frame
    pd.set_option('display.max_columns', None)

    # file to save tweets
    fetched_tweets_filename = "tweets.txt"
    f = open(fetched_tweets_filename, "a")

    # spark context definition
    sc = SparkContext("local[2]", "Twitter Demo")
    ssc = StreamingContext(sc, 10)

    # creating
    twitter_client = TwitterClient()
    tweet_analyzer = TweetAnalyzer()
    twitter_streamer = TwitterStreamer()

    # we will get tweets starting this date
    startDate = datetime.datetime(2019, 1, 1, 0, 0, 0)

    # get api from twitter
    api = twitter_client.get_twitter_client_api()

    # list
    """
    Making list of tuples (party list, leader name, party name)
    """
    likud_list = ["Benjamin Netanyahu", "Yuli Edelstein", "Yisrael Katz", "Gilad Erdan", "Gideon Saar", "Miri Regev",\
             "Yariv Levin", "Yoav Gallant", "Nir Barkat", "Gila Gamliel", "Avi Dichter", "Zeev Elkin", "Haim Katz",\
             "Tzachi Hanegbi", "Ofir Akunis", "Yuval Steinitz", "Tzipi Hotovely", "David Amsalem", "Amir Ohana",\
             "Ofir Katz", "Eti Atiya", "Yoav Kish", "David Bitan", "Keren Barak", "Shlomo Karhi",  "Zohar",\
             "Eli Ben Dahan", "Sharren Haskel", "Michal Shir", "Kathy Sheetrit", "Patin Mula", "May Golan",\
             "Uzi Dayan", "Ariel Kallner", "Osnat Mark", "Amit Halevy"]
    # creating tuple for all party items
    likud_tuple = (likud_list, "Benjamin Netanyahu", "likud")


    '''
    s = api.search(q="donald trump", from_date=startDate)
    for i in s:
        print(i)
        print(i.retweet_count)
        id = i.id
        retweets = api.retweets(id, 100)
        for retweet in retweets:
            print("retweet           ", retweet)           
    '''

    '''
    # loop trow tuple
    tuple_index = 0
    sum_of_3_tuple_items = 0
    for item in likud_tuple:

        tuple_index += 1
        if tuple_index == 1:
            sum_of_party_list = 0
            for hash_tag in item:
                sum_of_party_list += get_values_by_hashtag(hash_tag)
            sum_of_party_list = sum_of_party_list / len(item)

        else:
            sum_of_3_tuple_items += get_values_by_hashtag(item)

        sum_of_3_tuple_items += sum_of_party_list

    sum_of_3_tuple_items = sum_of_3_tuple_items / len(likud_tuple)
    print(sum_of_3_tuple_items)
    
    '''

    s = socket.socket()  # Create a socket object
    s.bind((twitter_credentials.HOST, twitter_credentials.PORT))  # Bind to the port

    print("Listening on port: %s" % str(twitter_credentials.PORT))

    s.listen(5)  # Now wait for client connection.
    c, addr = s.accept()  # Establish connection with client.

    print("Received request from: " + str(addr))

    twitter_streamer.stream_tweets(c, ["donald trump"])

    f.close()








