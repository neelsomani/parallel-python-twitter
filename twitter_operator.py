""" Twitter operations that can be parallelized. """

from abc import ABC
from functools import total_ordering
import logging
from typing import Any, Optional, Set

import twitter

LOGGER = logging.getLogger(__name__)


@total_ordering
class TwitterOp(ABC):
    """
    A Twitter API operator paired with an API key.
    """
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
