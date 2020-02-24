import os

TWITTER_API_CONSUMER_KEY = os.getenv('TWITTER_CONSUMER_KEY')
TWITTER_API_CONSUMER_SECRET = os.getenv('TWITTER_CONSUMER_SECRET')
if not TWITTER_API_CONSUMER_KEY or not TWITTER_API_CONSUMER_SECRET:
    raise ValueError('You need to set the Twitter environment variables')

FIREBASE_DB_URL = 'https://followers-c07b4.firebaseio.com'
FIREBASE_CRED = os.environ.get('FIREBASE_CONFIG')
if FIREBASE_CRED is None:
    raise ValueError('You must specify the Firebase config')
