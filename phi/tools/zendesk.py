from phi.tools import Toolkit
import json
import re
import requests

class ZendeskTools(Toolkit):
    """
    A toolkit class for interacting with the Zendesk API to search articles.
    It requires authentication details and the company name to configure the API access.
    """

    def __init__(self, username: str, password: str, company_name: str):
        """
        Initializes the ZendeskTools class with necessary authentication details
        and registers the search_zendesk method.

        Parameters:
        username (str): The username for Zendesk API authentication.
        password (str): The password for Zendesk API authentication.
        company_name (str): The company name to form the base URL for API requests.
        """
        super().__init__(name="zendesk_tools")
        self.username = username
        self.password = password
        self.company_name = company_name
        self.register(self.search_zendesk)

    def search_zendesk(self, search_string: str) -> str:
        """
        Searches for articles in Zendesk Help Center that match the given search string.

        Parameters:
        search_string (str): The search query to look for in Zendesk articles.

        Returns:
        str: A JSON-formatted string containing the list of articles without HTML tags.

        Raises:
        ConnectionError: If the API request fails due to connection-related issues.
        """
        auth = (self.username, self.password)
        url = f"https://{self.company_name}.zendesk.com/api/v2/help_center/articles/search.json?query={search_string}"
        try:
            response = requests.get(url, auth=auth)
            response.raise_for_status()
            clean = re.compile('<.*?>')
            articles = [re.sub(clean, '', article["body"]) for article in response.json()['results']]
            return json.dumps(articles)
        except requests.RequestException as e:
            raise ConnectionError(f"API request failed: {e}")