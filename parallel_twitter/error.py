""" Error classes. """

from typing import Dict, List

from twitter import TwitterError


class OutOfKeysError(Exception):
    """ Error for no valid API keys """

    @property
    def message(self):
        """ Returns the first argument used to construct this error. """
        return self.args[0]


def not_authorized_error(ex: TwitterError) -> bool:
    """
    Return whether the `TwitterError` is an authorization error. This would
    occur if we are requesting data from an account that is private.

    Parameters
    ----------
    ex : TwitterError
        An error raised by the Twitter API client
    """
    return isinstance(ex.message, str) and ex.message == 'Not authorized.'


def rate_limit_error(ex: TwitterError) -> bool:
    """
    Return whether the `TwitterError` is the result of a rate limit.

    Parameters
    ----------
    ex : TwitterError
        An error raised by the Twitter API client
    """
    if isinstance(ex.message, List) and isinstance(ex.message[0], Dict):
        code = ex.message[0]['code']
        # Rate limiting codes
        if code == 420 or code == 429 or code == 88:
            return True
    return False
