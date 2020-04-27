""" Run basic analyses using the Twitter API. """

from collections import defaultdict, deque
import logging
from typing import Any, Dict, List, Set

import twitter

from parallel_twitter.parallel_client import ParallelTwitterClient
from parallel_twitter.twitter_operator import (
    GetFriendIDs,
    GetUserTimeline,
    StatusesLookup,
    UsersLookup
)

LOGGER = logging.getLogger(__name__)


def calculate_industry_group(seed: List[int],
                             depth: int,
                             apis: List[twitter.Api],
                             max_count: int=200) -> Dict[int, int]:
    """
    Run a breadth-first search on a set of users' friends on Twitter.
    Return the number of followers each user has within the group of nth-degree
    connections.

    A depth of `k` means that we will not visit the friends of anyone who is
    more than `k` hops away from a seed user. Users who are exactly `k + 1`
    hops away will still be included in the output dictionary (since we know
    that at least one user follows them), but we will not count the users
    who they are following.

    Parameters
    ----------
    seed : List[int]
        List of Twitter user IDs to initialize the BFS
    depth : int
        The depth of the BFS. Defaults to 2.
    apis : List[twitter.Api]
        A list of twitter.Api objects, which can be obtained from
        `parallel_client.oauth_dicts_to_apis`
    max_count : int
        The maximum number of friends to pull for a given user
    """
    n_followers: Dict[int, int] = defaultdict(int)
    client = ParallelTwitterClient(apis=apis)
    LOGGER.info(
        'Pulled {} valid keys'.format(len(client.operators[GetFriendIDs]))
    )
    users_queue: deque = deque()
    for u in seed:
        users_queue.append((u, 0))
    depth_flags: Set[int] = set()
    while len(users_queue) > 0:
        u, n = users_queue.popleft()
        if n not in depth_flags:
            depth_flags.add(n)
            LOGGER.info('Reached depth: {}'.format(n))
            LOGGER.info('Size of queue: {}'.format(len(users_queue)))

        user_friends = client.get_friend_ids(user_id=u,
                                             max_count=max_count)
        for f in user_friends:
            if n < depth and f not in n_followers:
                users_queue.append((f, n + 1))
            n_followers[f] += 1
    return n_followers


def pull_users_posts(users: List[int],
                     apis: List[twitter.Api]) -> List[Dict[str, Any]]:
    """
    Return a list of the specified users' posts and the number of likes they
    received.

    TODO(@neel): Add a `since_unix_time` parameter.

    Parameters
    ----------
    users : List[int]
        List of Twitter API user IDs
    apis : List[twitter.Api]
        A list of twitter.Api objects, which can be obtained from
        `parallel_client.oauth_dicts_to_apis`
    """
    posts: List[Dict[str, Any]] = []
    client = ParallelTwitterClient(apis=apis)
    LOGGER.info(
        'Pulled {} valid keys'.format(len(client.operators[GetUserTimeline]))
    )
    for u in users:
        user_posts = client.get_user_timeline(user_id=u,
                                              trim_user=True,
                                              include_rts=False,
                                              exclude_replies=True,
                                              min_count=2000)
        posts.extend([{
            # Fields are set on the `Status` object by reflection
            'id': p.id,
            'user_id': p.user.id,
            'timestamp': p.created_at_in_seconds,
            'n_likes': p.favorite_count
        } for p in user_posts])
    return posts


def pull_hydrated_users(users: List[int],
                        apis: List[twitter.Api]) -> List[Dict[str, Any]]:
    """
    Return a list of dictionaries containing features for each user.

    Parameters
    ----------
    users : List[int]
        List of Twitter API user IDs
    apis : List[twitter.Api]
        A list of twitter.Api objects, which can be obtained from
        `parallel_client.oauth_dicts_to_apis`
    """
    client = ParallelTwitterClient(apis=apis)
    LOGGER.info(
        'Pulled {} valid keys'.format(len(client.operators[UsersLookup]))
    )
    return [
        {
            # Fields are set on the `User` object by reflection
            'id': u.id,
            'handle': u.screen_name,
            'location': u.location,
            'verified': u.verified,
            'followers': u.followers_count,
            'friends': u.friends_count
        } for u in client.users_lookup(users)
    ]


def pull_hydrated_posts(posts: List[int],
                        apis: List[twitter.Api]) -> List[Dict[str, Any]]:
    """
    Return a list of dictionaries containing the hydrated data for each
    tweet.

    Parameters
    ----------
    posts : List[int]
        List of post IDs from the Twitter API
    apis : List[twitter.Api]
        A list of twitter.Api objects, which can be obtained from
        `parallel_client.oauth_dicts_to_apis`
    """
    client = ParallelTwitterClient(apis=apis)
    LOGGER.info(
        'Pulled {} valid keys'.format(len(client.operators[StatusesLookup]))
    )
    return [
        {
            # Fields are set on the `Status` object by reflection
            'id': p.id,
            'user_id': p.user.id,
            'text': p.text,
            'full_text': p.full_text,
            'n_likes': p.favorite_count,
            'n_retweets': p.retweet_count,
            'location': p.location,
            'geo': p.geo,
            'url': 'https://www.twitter.com/{0}/status/{1}'.format(
                p.user.screen_name, p.id
            ),
            'timestamp': p.created_at_in_seconds

        } for p in client.statuses_lookup(posts)
    ]


def pull_users_likes(users: List[int],
                     apis: List[twitter.Api]) -> List[Dict[str, Any]]:
    """
    Return the last 200 posts that each of the specified users liked.

    Parameters
    ----------
    users : List[int]
        List of Twitter API user IDs
    apis : List[twitter.Api]
        A list of twitter.Api objects, which can be obtained from
        `parallel_client.oauth_dicts_to_apis`
    """
    client = ParallelTwitterClient(apis=apis)
    LOGGER.info(
        'Pulled {} valid keys'.format(len(client.operators[UsersLookup]))
    )
    posts = []
    for idx, u in enumerate(users):
        posts.extend([
            {
                # Fields are set on the `Status` object by reflection
                'id': p.id,
                'user_id': p.user.id,
                'timestamp': p.created_at_in_seconds,
                'n_likes': p.favorite_count,
                'favorited_by': u
            }
            for p in client.get_favorites(user_id=u, max_count=200)
        ])
    return posts


if __name__ == '__main__':
    log_format = '[%(asctime)s %(threadName)s, %(levelname)s] %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format, datefmt='%s')
