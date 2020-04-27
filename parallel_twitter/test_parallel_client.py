""" Tests for the parallel Twitter client. """

import pytest
from unittest.mock import patch

from parallel_twitter.error import OutOfKeysError
from parallel_twitter.mock_api import *
from parallel_twitter.parallel_client import ParallelTwitterClient


@patch('twitter.Api')
@patch('time.time')
def test_parallel_client_single_req_blocked(mock_time, mock_twitter):
    mock_time.return_value = 1000
    mock_twitter.return_value = MockBlockedApi(1001)
    p = ParallelTwitterClient(apis=[twitter.Api()])
    with pytest.raises(OutOfKeysError):
        p.get_friend_ids(screen_name='jack')


@patch('twitter.Api')
@patch('time.time')
@patch('time.sleep')
def test_parallel_client_valid_and_blocked(mock_sleep, mock_time, mock_twitter):
    mock_time.return_value = 1000
    mock_twitter.return_value = MockBlockedApi(1001)
    blocked = twitter.Api()
    mock_twitter.return_value = MockValidApi(['kanyewest'])
    valid = twitter.Api()
    p = ParallelTwitterClient(apis=[blocked, valid])
    p.get_friend_ids(screen_name='jack')
    assert not mock_sleep.called


@patch('twitter.Api')
@patch('time.time')
@patch('time.sleep')
def test_parallel_client_sleep(mock_sleep, mock_time, mock_twitter):
    mock_time.return_value = 1000
    mock_twitter.return_value = MockSingleBlockedApi(1001, ['kanyewest'])
    blocked_once = twitter.Api()
    p = ParallelTwitterClient(apis=[blocked_once])
    # The call should prompt a sleep then succeed.
    p.get_friend_ids(screen_name='jack')
    assert mock_sleep.called


@patch('twitter.Api')
@patch('time.time')
@patch('time.sleep')
def test_parallel_client_staggers_requests(mock_sleep, mock_time, mock_twitter):
    mock_time.return_value = 1000
    mock_twitter.return_value = MockValidApi(['kanyewest'])
    valid = twitter.Api()
    p = ParallelTwitterClient(apis=[valid])
    p.get_friend_ids(screen_name='jack')
    assert not mock_sleep.called
    # Not enough time has elapsed, so parallel client should sleep
    mock_time.return_value = 1001
    p.get_friend_ids(screen_name='jack')
    assert mock_sleep.called

