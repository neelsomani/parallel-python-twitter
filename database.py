""" Wrapper for the Firebase DB. """

from typing import Dict, List

import firebase_admin
from firebase_admin import credentials, db

from constants import FIREBASE_CRED, FIREBASE_DB_URL

USERS_BUCKET = 'users'
firebase_admin.initialize_app(credentials.Certificate(FIREBASE_CRED),
                              options={'databaseURL': FIREBASE_DB_URL})


def get_all_api_keys() -> List[Dict[str, str]]:
    """
    Get a list of all API key `dicts`. Each `dict` will contain a
    Twitter OAuth token and an OAuth secret.
    """
    users = db.reference('%s' % USERS_BUCKET).get()
    assert isinstance(users, Dict)
    keys = []
    for u in users:
        keys.append({
            'oauth_token': users[u]['oauth_token'],
            'oauth_token_secret': users[u]['oauth_token_secret']
        })
    return keys
