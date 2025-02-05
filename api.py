import requests

class Scraper():
    """
    A class to scrape bus data from the LPP API.
    """

    def __init__(self):
        """
        Initializes the API client with a base URL and a session.
        Attributes:
            base_url (str): The base URL for the API.
            session (requests.Session): The session object for making HTTP requests.
        """
        self.base_url = "https://www.lpp.si/lpp/ajax/1/"
        self.session = requests.Session()

    def get_line(self, line: str) -> dict:
        """
        Fetches data for a specific bus line.
        Args:
            line (str): The bus line identifier.
        Returns:
            dict: The JSON response from the API containing the bus line data.
        """
        url = self.base_url + line
        response = self.session.get(url)
        return response.json()
    
    def all_buses(self, line: str) -> list:
        """
        Retrieve all bus keys for a given line.
        Args:
            line (str): The bus line identifier.
        Returns:
            list: A list of bus keys for the specified line.
        """
        data = self.get_line(line)
        buses = []
        for bus in data:
            buses.append(bus[0]['key'])
        return buses
    
    def filter_line(self, line: str, key: int | str | list) -> list:
        """
        Filters the bus data based on the provided key.
        Args:
            line (str): The line identifier to fetch the bus data.
            key (int | str | list): The key to filter the bus data. It can be an integer, string, or list of integers/strings.
        Returns:
            list: A list of buses that match the provided key.
        """
        data = self.get_line(line)

        try:
            key = int(key)
        except:
            pass

        if isinstance(key, int) or isinstance(key, str):
            return [bus for bus in data if bus[0]['key'] == key]
        elif isinstance(key, list):
            return [bus for bus in data if str(bus[0]['key']) in key or bus[0]['key'] in key]
        
if __name__ == "__main__":
    scraper = Scraper()
    # print(scraper.get_line("Drama", "to_center"))