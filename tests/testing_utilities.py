import json
from django.contrib.auth.models import User


def populate_test_db():
    """
    Adds records to an empty test database
    """
    User.objects.create_user(
        username='admin',
        email='admin@reti.it',
        password='secretpassword')


def login_client_user(self):
    self.client.login(username='admin', password='secretpassword')
    return self


def logout_client_user(self):
    self.client.logout()
    return self


def is_json(myjson):
    """
    tests if a string is valid JSON
    """
    try:
        json_object = json.loads(myjson)
    except ValueError:
        return False
    return True
