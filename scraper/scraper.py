import csv
import json
import praw
import re
import requests
import numpy as np

from csv import reader
from datetime import datetime, timedelta


def get_subreddit(name):
    if name == "":
        sub = "wallstreetbets"

    with open("config.json") as config:
        config = json.load(config)

    # create reddit instance
    reddit = praw.Reddit(client_id=config["login"]["client_id"], client_secret=config["login"]["client_secret"],
                         username=config["login"]["username"], password=config["login"]["password"],
                         user_agent=config["login"]["user_agent"])

    # create a subreddit instance
    subreddit = reddit.subreddit(name)
    return subreddit


def get_tickers():
    with open('tickers.txt', 'r') as w:
        tickers = w.readlines()
        tickers_list = []

        for ticker in tickers:
            ticker = ticker.replace('\n', '')
            tickers_list.append(ticker)

        return tickers_list


def get_all_submissions_id(subreddit):
    # scrape submissions created from 9pm two days ago to 9pm one day ago at 12 midnight
    # this is to avoid scraping newly created submissions
    current_time = datetime.now() + timedelta(hours=10)

    submissions_id = []

    for submission in subreddit.new(limit=1000):
        submission_date = datetime.utcfromtimestamp(submission.created)
        submission_delta = current_time - submission_date

        link = 'www.reddit.com' + submission.permalink
        submission_delta = str(submission_delta)

        if 'day' not in submission_delta:
            submissions_id.append(link.split('/')[-3])

    return submissions_id


def get_all_comments_id(submissions_id):
    comments_id = []

    for submission_id in submissions_id:
        try:
            html = requests.get(f'https://api.pushshift.io/reddit/submission/comment_ids/{submission_id}')
            curr_comments_id = html.json()["data"]

            comments_id += curr_comments_id
        except:
            pass

    return comments_id


def get_all_comments(comments_id):
    comments_number = len(comments_id)
    comments_id = np.array(comments_id)
    comments = []

    # split the comments id to a group of 1000
    # to fit the pushshift API requirement
    i = 0
    while i < len(comments_id):
        print(str(len(comments_id)) + " / " + str(comments_number))
        next_comments_list = ",".join(comments_id[0:1000])
        next_comments = _get_comments(next_comments_list)
        comments += next_comments

        remove_me = slice(0, 1000)
        comments_id = np.delete(comments_id, remove_me)

    return comments


def _get_comments(comments_id):
    try:
        html = requests.get(f'https://api.pushshift.io/reddit/comment/search?ids={comments_id}&fields=body&size=1000')
        comments = html.json()['data']
    except:
        pass

    return comments


def output_comments(comments, tickers):
    result = _create_dict()

    for comment in comments:
        for ticker in tickers:
            if _check_comment(ticker, comment['body']):
                result[ticker]["comments"].append(re.sub(r"\s", " ", comment['body']))

    with open("../sentiment/result.json", "w") as outfile:
        json.dump(result, outfile, indent=4)

    return result


def _check_comment(word, body):
    return re.compile(r'\b({0})\b'.format(word), flags=re.IGNORECASE).search(body) is not None


def _create_dict():
    result = {}
    with open("tickers.csv") as tickers:
        tickers = reader(tickers)
        header = next(tickers)

        # Check file as empty
        if header is not None:
            # Iterate over each row after the header in the csv
            for ticker in tickers:
                # row variable is a list that represents a row in csv
                result[ticker[0]] = {
                    'symbol': ticker[0],
                    'name': ticker[1],
                    'sector': ticker[2],
                    'common_name': ticker[3],
                    'comments': []
                }

    return result


def run(name):
    # create subreddit instance
    subreddit = get_subreddit(name)

    # get tickers list
    tickers = get_tickers()

    # get all submissions id within the last 24 hours
    submissions_id = get_all_submissions_id(subreddit)

    # get all comments id from all the submissions
    comments_id = get_all_comments_id(submissions_id)

    # get all comments from the comments id
    comments = get_all_comments(comments_id)

    # output comments to a json file
    output_comments(comments, tickers)


if __name__ == "__main__":
    name = "wallstreetbets"

    run(name)
