# parallel-python-twitter
![Travis CI](https://travis-ci.org/neelsomani/parallel-python-twitter.svg?branch=master)

A client that distributes Twitter API requests across multiple keys. Built for Python 3.6.

## Getting Started

First, get your API credentials together and get a list of `twitter.Api` objects:

```
import parallel_twitter
TWITTER_API_CONSUMER_KEY = ...
TWITTER_API_CONSUMER_SECRET = ...
OAUTHS = [
    {
        'oauth_token': ...,
        'oauth_token_secret': ...
    },
    {
        'oauth_token': ...,
        'oauth_token_secret': ...
    },
    ...
]
apis = parallel_twitter.oauth_dicts_to_apis(
    oauth_dicts=OAUTHS,
    api_consumer_key=TWITTER_API_CONSUMER_KEY,
    api_consumer_secret=TWITTER_API_CONSUMER_SECRET
)
```

Next, try out some of the examples:

```
user_ids = [
    561808704, # @neeljsomani
    813286, # @BarackObama
    17919972 # @taylorswift13
]
# Get a list of posts that these users liked
parallel_twitter.examples.pull_users_likes(
    users=user_ids,
    apis=apis
)
# Get a list of these users' posts + number of likes
parallel_twitter.examples.pull_users_posts(
    users=user_ids,
    apis=apis
)
```

## Comparison with Twint

[Twint](https://github.com/twintproject/twint/) is a Python library for scraping data from Twitter.

1. From Twint's [documentation](https://github.com/twintproject/twint/wiki/Home/bf04df20a7978ab7f2e39da70a6f85ba70f758cf): "Twitter limits scrolls while browsing the user timeline. This means that with .Profile or with .Favorites you will be able to get ~3200 tweets." There are no such limits if you distribute your requests using `parallel-python-twitter`.
2. Twitter will block your requests if you scrape enough (ex: https://github.com/twintproject/twint/issues/682). I've tested `parallel-python-twitter` up to 100s of megabytes.
3. Technically, `twint` violates Twitter's Terms of Service, since scraping is not permitted in general.
