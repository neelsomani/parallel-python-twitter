""" Objects to mock the Twitter API. """

from typing import Any, List

import twitter
from twitter.ratelimit import EndpointRateLimit


class MockBlockedApi:
    """ An API key where the rate limit reset time is stale """
    def __init__(self, renewal_time: int):
        self.renewal_time = renewal_time

    def GetFriendIDs(self, **params: Any) -> List[str]:
        raise twitter.TwitterError('Rate limit exceeded')

    def CheckRateLimit(self, *params: Any) -> EndpointRateLimit:
        return EndpointRateLimit(limit=15,
                                 remaining=0,
                                 reset=self.renewal_time)


class MockValidApi:
    """ An API key with no rate limit """
    def __init__(self, response: List[str]):
        self.response = response

    def GetFriendIDs(self, **params: Any) -> List[str]:
        return self.response

    def CheckRateLimit(self, *params: Any) -> EndpointRateLimit:
        return EndpointRateLimit(limit=15,
                                 remaining=15,
                                 reset=0)


class MockSingleBlockedApi:
    """ Make the ParallelTwitterClient wait before succeeding """
    def __init__(self, renewal_time: int, response: List[str]):
        self.renewal_time = renewal_time
        self.response = response

    def GetFriendIDs(self, **params: Any) -> List[str]:
        return self.response

    def CheckRateLimit(self, *params: Any) -> EndpointRateLimit:
        return EndpointRateLimit(limit=15,
                                 remaining=0,
                                 reset=self.renewal_time)
