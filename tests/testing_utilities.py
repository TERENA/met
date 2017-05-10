import json
import time
from django.contrib.auth.models import User
#from my_application.models import Category, Thing

def populate_test_db():
    """
    Adds records to an empty test database
    """
    #cat = Category.objects.create(cat_name='Widgets')
    #cat_inactive = Category.objects.create(cat_name='Inactive Category',
    #                                        cat_active=False)
    #thing1 = Thing.objects.create(category=cat,
    #                            thing_desc="Test Thing",
    #                            thing_model="XYZ1234",
    #                            thing_brand="Brand X")

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
    except ValueError, e:
        return False
    return True
