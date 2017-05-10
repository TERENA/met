from pyvirtualdisplay import Display
from selenium import webdriver
from django.core.urlresolvers import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.utils import formats
from ..testing_utilities import populate_test_db


class FunctionalTest(StaticLiveServerTestCase):
    def setUp(self):
        display = Display(visible=0, size=(800, 600))
        display.start()

        self.selenium = webdriver.Firefox()
        self.selenium.implicitly_wait(3)
        populate_test_db()

    def tearDown(self):
        self.selenium.quit()

    # Auxiliary function to add view subdir to URL
    def _get_full_url(self, namespace):
        return self.live_server_url + namespace

    def _is_text_present(self, text):
        try:
            body = self.selenium.find_element_by_tag_name("body") # find body tag element
        except NoSuchElementException, e:
            return False
        return text in body.text # check if the text is in body's text

    def test_home_title(self):
        """
        Tests that Home is loading properly
        """
        self.selenium.get(self._get_full_url("/"))
        self.assertIn(u'Metadata Explorer Tool', self.selenium.title)

    def test_home_sections(self):
        """
        Tests that Home is showing the right sections
        """
        self.selenium.get(self._get_full_url("/"))
        self.assertTrue(self._is_text_present("Entities summary"))
