""" Twitter operations that can be parallelized. """

from abc import ABC
from functools import total_ordering
import logging
from typing import Any, List, Optional, Set, Tuple

import twitter

LOGGER = logging.getLogger(__name__)


@total_ordering
class TwitterOp(ABC):
    """
    A Twitter API operator paired with an API key.
    """

    reqs_per_minute = 1

    def __init__(self, api: twitter.Api, unique_id: Optional[int] = None):
        """
        Raise a `TwitterError` if the API key is invalid. The caller is
        responsible for handling the error appropriately.

        Parameters
        ----------
        api : twitter.Api
            A Twitter API object to make requests through
        unique_id : Optional[int]
            An ID to identify this operator instance
        """
        self.api = api
        self.unique_id = unique_id
        self.renewal_time = 0
        self._reset_renewal_time()

    def invoke(self, *args: Any) -> Any:
        """ Execute the Twitter API call. Raise a `TwitterError` if the API
        call is unsuccessful."""
        try:
            return self._invoke(*args)
        except twitter.TwitterError as ex:
            self._reset_renewal_time()
            raise ex

    def _invoke(self, *args: Any) -> Any:
        raise NotImplementedError

    @property
    def rate_limit_endpoint(self) -> str:
        """
        The name of the endpoint to pass to `twitter.api.CheckRateLimit`
        to get the current rate limit.
        """
        raise NotImplementedError

    def _reset_renewal_time(self) -> None:
        """
        Reset the renewal time for this API key if necessary.
        """
        rate_limit = self.api.CheckRateLimit(self.rate_limit_endpoint)
        if rate_limit.remaining == 0:
            LOGGER.info('Setting the renewal time for {0} to {1}'.format(
                self, rate_limit.reset))
            self.renewal_time = rate_limit.reset

    def __eq__(self, other):
        return self.renewal_time == other.renewal_time

    def __lt__(self, other):
        return self.renewal_time < other.renewal_time

    def __repr__(self):
        return 'TwitterOp[ID={}]'.format(self.unique_id)


class GetFriendIDs(TwitterOp):
    """
    An operator to get the IDs of the users that the requested user is
    following.
    """
    def _invoke(self,
                user_id: Optional[int] = None,
                screen_name: Optional[str] = None,
                max_count: Optional[int] = None) -> Set[int]:
        """
        Return the users that the specified user is following.

        Parameters
        ----------
        user_id : Optional[int]
            The Twitter ID of the specified user
        screen_name : Optional[str]
            The Twitter handle of the specified user
        max_count : Optional[int]
            The maximum number of friends to return. Defaults to 5000.
        """
        return set(self.api.GetFriendIDs(user_id=user_id,
                                         screen_name=screen_name,
                                         total_count=max_count))

    @property
    def rate_limit_endpoint(self) -> str:
        return '/friends/ids.json'


class GetFollowerIDs(TwitterOp):
    """
    An operator to get the IDs of the users that are following the requested
    user.
    """
    def _invoke(self,
                user_id: Optional[int] = None,
                screen_name: Optional[str] = None,
                cursor: int = -1,
                max_count: Optional[int] = None) -> Tuple[int, int, List[int]]:
        """
        Return the users that are following the specified user.

        Parameters
        ----------
        user_id : Optional[int]
            The Twitter ID of the specified user
        screen_name : Optional[str]
            The Twitter handle of the specified user
        cursor : int
            Cursor to identify the page to pull, starting at -1
        max_count : Optional[int]
            The maximum number of friends to return. Defaults to 5000.
        """
        return self.api.GetFollowerIDsPaged(
            user_id=user_id,
            screen_name=screen_name,
            cursor=cursor,
            count=max_count
        )

    @property
    def rate_limit_endpoint(self) -> str:
        return '/followers/ids.json'


class GetUserTimeline(TwitterOp):
    """
    An operator to get the posts on a user's timeline.
    """

    reqs_per_minute = 60

    def _invoke(
            self,
            user_id: Optional[int] = None,
            screen_name: Optional[str] = None,
            trim_user: Optional[bool] = False,
            include_rts: Optional[bool] = True,
            exclude_replies: Optional[bool] = False,
            max_id: Optional[int] = None
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
        max_id : Optional[int]
            Only return posts older than or equal to the specified ID. Defaults
            to None.
        """
        return self.api.GetUserTimeline(user_id=user_id,
                                        screen_name=screen_name,
                                        trim_user=trim_user,
                                        include_rts=include_rts,
                                        exclude_replies=exclude_replies,
                                        count=200,
                                        max_id=max_id)

    @property
    def rate_limit_endpoint(self) -> str:
        return '/statuses/user_timeline.json'


class UsersLookup(TwitterOp):
    """
    Hydrate a list of user IDs.
    """

    reqs_per_minute = 60

    def _invoke(self, user_ids: List[int]) -> List[twitter.User]:
        """
        Return a list of hydrated `User` objects.

        Parameters
        ----------
        user_ids : List[int]
            List of Twitter IDs to hydrate
        """
        return self.api.UsersLookup(user_id=user_ids)

    @property
    def rate_limit_endpoint(self) -> str:
        return '/users/lookup.json'


class StatusesLookup(TwitterOp):
    """
    Hydrate a list of post IDs.
    """

    reqs_per_minute = 60

    def _invoke(self, post_ids: List[int]) -> List[twitter.Status]:
        """
        Return a list of hydrated `Status` objects.

        Parameters
        ----------
        post_ids : List[int]
            List of Twitter post IDs to hydrate
        """
        return self.api.GetStatuses(status_ids=post_ids,
                                    include_entities=True)

    @property
    def rate_limit_endpoint(self) -> str:
        return '/statuses/lookup.json'


class GetFavorites(TwitterOp):
    """
    Get a list of the specified user's favorited tweets.
    """

    reqs_per_minute = 5

    def _invoke(self,
                user_id: Optional[int] = None,
                screen_name: Optional[str] = None,
                max_count: Optional[int] = 200) -> List[twitter.Status]:
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
        return self.api.GetFavorites(user_id=user_id,
                                     screen_name=screen_name,
                                     count=max_count,
                                     include_entities=False)

    @property
    def rate_limit_endpoint(self) -> str:
        return '/favorites/list.json'
