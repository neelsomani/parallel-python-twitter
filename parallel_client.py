""" A wrapper for the Twitter API to parallelize requests across multiple
API keys. """

import logging
import time
from typing import Any, Dict, List, Optional, Type
import heapq

import twitter
from twitter import TwitterError

from error import OutOfKeysError, not_authorized_error, rate_limit_error
from twitter_operator import GetFriendIDs, TwitterOp

LOGGER = logging.getLogger(__name__)


class ParallelTwitterClient:
    """ A Twitter client to distribute requests across multiple API keys. """
    def __init__(self, apis: List[twitter.Api]):
        self.operators: Dict[Type[TwitterOp], List[TwitterOp]] = {
            GetFriendIDs: _api_keys_to_ops(apis, GetFriendIDs)
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
        # Assuming 15 requests / 15 minutes, we should stagger at about
        # 1 request per minute per key
        if time_since_last < 60 / len(self.operators[fn]):
            time.sleep(60 / len(self.operators[fn]) - time_since_last)
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

    def get_friend_ids(self,
                       user_id: Optional[int] = None,
                       screen_name: Optional[str] = None,
                       max_count: Optional[int] = None) -> List[int]:
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
