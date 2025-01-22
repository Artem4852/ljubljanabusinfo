import requests
import json

class Scraper():
    def __init__(self):
        self.base_url = "https://www.lpp.si/lpp/ajax/1/"
        self.session = requests.Session()

    def get_line(self, line):
        url = self.base_url + line
        response = self.session.get(url)
        return response.json()
    
    def filter_line(self, line, key: int | str | list):
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
    print(scraper.filter_line("101051", [6, 11, "19I"]))