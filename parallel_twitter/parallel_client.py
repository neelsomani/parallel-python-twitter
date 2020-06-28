""" A wrapper for the Twitter API to parallelize requests across multiple
API keys. """

import logging
import time
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Type
)
import heapq

import twitter
from twitter import TwitterError

from parallel_twitter.error import OutOfKeysError, not_authorized_error, rate_limit_error
from parallel_twitter.twitter_operator import (
    GetFavorites,
    GetFollowerIDs,
    GetFriendIDs,
    GetUserTimeline,
    StatusesLookup,
    TwitterOp,
    UsersLookup
)

LOGGER = logging.getLogger(__name__)


class ParallelTwitterClient:
    """ A Twitter client to distribute requests across multiple API keys. """
    OPERATORS = [
        GetFavorites,
        GetFollowerIDs,
        GetFriendIDs,
        GetUserTimeline,
        StatusesLookup,
        UsersLookup
    ]

    def __init__(self, apis: List[twitter.Api]):
        self.operators: Dict[Type[TwitterOp], List[TwitterOp]] = {
            op: _api_keys_to_ops(apis, op)
            for op in ParallelTwitterClient.OPERATORS
        }
        for op in self.operators:
            heapq.heapify(self.operators[op])
        self.last_call = 0.0
        self.n_requests = 0

    def _parallel_call(self, fn: Type[TwitterOp], *params: Any) -> Any:
        """
        Return a call using the stored API keys, ordering the API keys
        by the cached API rate limit reset times.

        Raise an `OutOfKeysError` if all cached times were invalid or if
        there are no valid API keys.

        Parameters
        ----------
        fn : Type[TwitterOp]
            A class type which implements the `TwitterOp` abstract class
        params : Any
            Parameters to pass to the `TwitterOp`
        """
        time_since_last = time.time() - self.last_call
        # Stagger at about `reqs_per_minute` requests per minute per key
        stagger_rate = 60 / len(self.operators[fn]) / fn.reqs_per_minute
        if time_since_last < stagger_rate:
            time.sleep(stagger_rate - time_since_last)
        self.last_call = time.time()

        self.n_requests += 1
        if self.n_requests % 100 == 0:
            LOGGER.info('Executing the {}th request...'.format(self.n_requests))

        attempted_keys: List[TwitterOp] = []
        for _ in range(len(self.operators[fn])):
            op = heapq.heappop(self.operators[fn])
            if op.renewal_time > time.time():
                LOGGER.info('Renewal time for {0} is {1}'
                            .format(op, op.renewal_time))
                time.sleep(op.renewal_time - time.time() + 1)
            try:
                result = op.invoke(*params)
                attempted_keys.append(op)
                _add_all_to_heap(attempted_keys, self.operators[fn])
                return result
            except TwitterError as ex:
                LOGGER.info('Twitter API error for {0} with params {1}: {2}'
                            .format(op, params, ex))
                if not_authorized_error(ex) or rate_limit_error(ex):
                    attempted_keys.append(op)
                if not_authorized_error(ex):
                    # We should ignore requests for users with private accounts
                    _add_all_to_heap(attempted_keys, self.operators[fn])
                    return []

        _add_all_to_heap(attempted_keys, self.operators[fn])
        raise OutOfKeysError(
            'Could not find a valid key for operator {0} and params {1}'
            .format(fn, params))

    def get_followers(
            self,
            user_id: Optional[int] = None,
            screen_name: Optional[str] = None,
            min_count: int = 1,
            batch_size: int = 5000,
            streaming_fn: Optional[Callable[[twitter.User], Any]] = None
        ) -> List[Any]:
        """
        Make multiple API requests to pull a user's Twitter following.
        You can specify how many users to pull with each request in
        addition to the minimum number of total users to pull.

        Parameters
        ----------
        user_id : Optional[int]
            The Twitter ID of the specified user
        screen_name : Optional[str]
            The Twitter handle of the specified user
        min_count : Optional[int]
            The minimum number of twitter.User objects to pull.
            Users are fetched in increments of `batch_size`per request.
            Defaults to 1.
        batch_size : int
            The number of user IDs to request from the API for each pull.
        streaming_fn : Optional[Callable[[twitter.User], Any]]
            If specified, this function will be executed on the returned
            users row by row, only holding `batch_size` twitter.User objects
            at a time.
        """
        batch_size = min(batch_size, min_count)
        next_cursor, prev_cursor, fn_result = -1, None, []
        users_count = 0
        while True:
            next_cursor, prev_cursor, user_ids = self._parallel_call(
                GetFollowerIDs,
                user_id,
                screen_name,
                next_cursor,
                batch_size
            )
            if streaming_fn:
                users = self.users_lookup(user_ids)
                stream = [streaming_fn(u) for u in users]
                fn_result.extend([v for v in stream if v is not None])
            else:
                fn_result.extend(user_ids)
            users_count += len(user_ids)
            if next_cursor == 0 \
                    or next_cursor == prev_cursor \
                    or users_count >= min_count:
                break
        return fn_result

    def get_friend_ids(self,
                       user_id: Optional[int] = None,
                       screen_name: Optional[str] = None,
                       max_count: Optional[int] = None) -> Set[int]:
        """
        Get the users that the specified user is following.

        Parameters
        ----------
        user_id : Optional[int]
            The Twitter ID of the specified user
        screen_name : Optional[str]
            The Twitter handle of the specified user
        max_count : Optional[int]
            The maximum number of friends to return. Defaults to 5000.
        """
        return self._parallel_call(GetFriendIDs,
                                   user_id,
                                   screen_name,
                                   max_count)

    def get_user_timeline(
            self,
            user_id: Optional[int] = None,
            screen_name: Optional[str] = None,
            trim_user: Optional[bool] = False,
            include_rts: Optional[bool] = True,
            exclude_replies: Optional[bool] = False,
            min_count: int = 1,
            max_requests: int = 100000
    ) -> List[twitter.Status]:
        """
        Return the posts on the specified user's timeline.

        Parameters
        ----------
        user_id : Optional[int]
            The Twitter ID of the specified user
        screen_name : Optional[str]
            The Twitter handle of the specified user
        trim_user : Optional[bool]
            If True, include only a user ID rather than the full user object.
            Defaults to False.
        include_rts : Optional[bool]
            If True, include the retweets on the user's timeline. Defaults to
            True.
        exclude_replies : Optional[bool]
            If True, do not include posts that were replies. Defaults to False.
        min_count : Optional[int]
            The minimum number of posts to return. Posts are fetched in
            increments of 200 per request. Defaults to 1.
        max_requests : int
            The maximum number of API requests to use. Defaults to 100000.
        """
        posts: List[twitter.Status] = []
        max_id: Optional[int] = None
        calls = 0
        while len(posts) < min_count and calls < max_requests:
            current_posts = self._parallel_call(GetUserTimeline,
                                                user_id,
                                                screen_name,
                                                trim_user,
                                                include_rts,
                                                exclude_replies,
                                                max_id)
            # Return if there are no unseen posts
            if len(current_posts) == 0 or \
                    len(current_posts) == 1 and current_posts[0].id == max_id:
                return posts
            # Throw away the post that is equal to max_id
            if current_posts[0].id == max_id:
                current_posts.pop(0)
            max_id = min(p.id for p in current_posts)
            posts.extend(current_posts)
            calls += 1
        return posts

    def users_lookup(self, user_ids: List[int]) -> List[twitter.User]:
        """
        Return a list of hydrated `User` objects.

        Parameters
        ----------
        user_ids : List[int]
            List of Twitter IDs to hydrate
        """
        if len(user_ids) == 0:
            return []
        users: List[twitter.User] = []
        for i in range((len(user_ids) - 1) // 100 + 1):
            users.extend(self._parallel_call(
                UsersLookup,
                user_ids[100 * i: 100 * (i + 1)]
            ))
        return users

    def statuses_lookup(self, post_ids: List[int]) -> List[twitter.Status]:
        """
        Return a list of hydrated `Status` objects.

        Parameters
        ----------
        post_ids : List[int]
            List of Twitter post IDs to hydrate
        """
        if len(post_ids) == 0:
            return []
        posts: List[twitter.Status] = []
        for i in range((len(post_ids) - 1) // 100 + 1):
            posts.extend(self._parallel_call(
                StatusesLookup,
                post_ids[100 * i: 100 * (i + 1)]
            ))
        return posts

    def get_favorites(
            self,
            user_id: Optional[int] = None,
            screen_name: Optional[str] = None,
            max_count: Optional[int] = 200
    ) -> List[twitter.Status]:
        """
        Return a list of `Status` objects which the user favorited.

        Parameters
        ----------
        user_id : Optional[int]
            The Twitter ID of the specified user
        screen_name : Optional[str]
            The Twitter handle of the specified user
        max_count : Optional[int]
            The maximum number of posts to return with a maximum of 200.
            Defaults to 200.
        """
        return self._parallel_call(GetFavorites,
                                   user_id,
                                   screen_name,
                                   max_count)


def oauth_dicts_to_apis(oauth_dicts: List[Dict[str, str]],
                        api_consumer_key: str,
                        api_consumer_secret: str) -> List[twitter.Api]:
    """ Convert a list of dictionaries to a list of Twitter API objects.
    Each dictionary should contain a key for `oauth_token` and a key
    for `oauth_token_secret`.

    Parameters
    ----------
    oauth_dicts : List[Dict[str, str]]
        A list of dictionaries representing valid OAuth tokens.
        There should be a key for `oauth_token` and a key for
        `oauth_token_secret`
    api_consumer_key : str
        Twitter API consumer key to be used for all
        `twitter.Api` objects
    api_consumer_secret : str
        Twitter API consumer secret to be used for all
        `twitter.Api` objects
    """
    apis = []
    for o in oauth_dicts:
        apis.append(
            twitter.Api(
                consumer_key=api_consumer_key,
                consumer_secret=api_consumer_secret,
                access_token_key=o['oauth_token'],
                access_token_secret=o['oauth_token_secret']
            )
        )
    return apis


def _add_all_to_heap(lst: List[TwitterOp], heap: List[TwitterOp]) -> None:
    """ Add all elements to a heap. """
    for o in lst:
        heapq.heappush(heap, o)


def _api_keys_to_ops(apis: List[twitter.Api],
                     op: Type[TwitterOp]) -> List[TwitterOp]:
    """ Map a list of Twitter API keys to a list of `TwitterOp` objects. """
    ops: List[TwitterOp] = []
    for k in apis:
        try:
            ops.append(op(api=k, unique_id=len(ops)))
        except TwitterError:
            # Throw away API keys that have errors.
            pass
    return ops
