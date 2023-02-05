
import re
import json
import urllib
from pathlib import Path

import requests
from bs4 import BeautifulSoup


class TruckScout24Scraper:

    """Web Scraper for TruckScout24 Website"""

    WEBSITE_URL = "https://www.truckscout24.de"
    WEBSITE_CATALOG_URL = WEBSITE_URL + "/transporter/gebraucht/kuehl-iso-frischdienst/renault"

    def __init__(self, path_to_dir) -> None:
        self.path_to_dir = path_to_dir
        self.__data = {"ads": []}
        self.__page_no = 1

        self.__create_dir(self.path_to_dir)

    def __create_dir(self, dir_name) -> None:
        """Creates a new directory. Ignores exception if the directory already exists"""

        Path(dir_name).mkdir(parents=True, exist_ok=True)

    def __parse_page(self, url) -> BeautifulSoup:
        """Parses an HTML page"""

        response = requests.get(url, timeout=5)
        return BeautifulSoup(response.text, "lxml") if response.status_code == 200 else None

    def __get_tag_data(self, tag) -> str:
        """Gets text from tag if tag exists"""

        return tag.get_text().strip() if tag else ""

    def __get_div_param(self, tags, param_name, param_class, value_class) -> str:
        """Gets a specific parameter value from a list of tags"""

        for tag in tags:
            if self.__get_tag_data(tag.find("div", {"class": param_class})) == param_name:
                return self.__get_tag_data(tag.find("div", {"class": value_class}))
        return ""

    def __convert_str_to_int(self, text) -> int:
        """Converts a string type with a number to an integer type"""

        num_str = re.search(r"\d+.{0,1}\d*", text)
        return int(num_str.group(0).replace(".", "_")) if num_str else 0

    def __get_description(self, description_tag) -> str:
        """Gets full truck description"""

        if description_tag:
            title_tag = description_tag.find("label", {"class": "sc-expandable-box__label"})
            title = title_tag.text.strip() + "\n\n" if title_tag else ""
            body_tag = description_tag.find("div", {"class": "short-description", "data-type": "description"})
            body = "\n".join(map(lambda s: s.strip(), body_tag.get_text().splitlines())) if body_tag else ""
            return title + body
        return ""

    def __get_page_config(self, page, page_url) -> dict:
        """Creates a truck configuration from the HTML page"""

        title_tag = page.find("h1", {"class": "sc-ellipsis sc-font-xl"})
        price_tag = page.find("h2", {"class": "sc-highlighter-4 sc-highlighter-xl sc-font-bold"})
        basic_data_tags = page.find("div", {"class": "data-basic"}).find_all("div", {"class": "itemspace"})
        specification_tags = page.find("div", {"class": "sc-expandable-box__content sc-grid-row"}).find_all("li")
        description_tag = page.find("div", {"class": "sc-expandable-box", "data-target": "[data-item-name='description']"})

        config = {}
        config["id"] = self.__page_no
        config["href"] = page_url
        config["title"] = self.__get_tag_data(title_tag)
        config["price"] = self.__convert_str_to_int(self.__get_tag_data(price_tag))
        config["mileage"] = self.__convert_str_to_int(self.__get_div_param(basic_data_tags, "Kilometer", "itemlbl", "itemval"))
        config["color"] = self.__get_div_param(specification_tags, "Farbe", "sc-font-bold", "")
        config["power"] = self.__convert_str_to_int(self.__get_div_param(specification_tags, "Leistung", "sc-font-bold", ""))
        config["description"] = self.__get_description(description_tag)

        return config

    def __download_images(self, page, image_num=3) -> None:
        """Downloads provided number of truck images from the HTML page"""

        image_tags = page.find_all("img", {"class": "gallery-picture__image sc-lazy-image lazyload"})
        image_num = image_num if len(image_tags) >= image_num else len(image_tags)
        images = list(map(lambda img: img.get("data-src"), image_tags[:image_num]))
        self.__create_dir(f"{self.path_to_dir}/{self.__page_no}")
        for i in range(image_num):
            image_url = images[i]
            image_extension = image_url.split(".")[-1]
            urllib.request.urlretrieve(image_url, f"{self.path_to_dir}/{self.__page_no}/image_{i+1}.{image_extension}")

    def __save_json_data(self, data_dict, path) -> None:
        """Saves a dict to JSON file"""

        json_data_file = open(path, "w", encoding="UTF-8")
        json.dump(data_dict, json_data_file, ensure_ascii=False)
        json_data_file.close()

    def process(self) -> None:
        """Collects data from TruckScout24 website and saves the results"""

        while True:
            catalog_page = self.__parse_page(TruckScout24Scraper.WEBSITE_CATALOG_URL + f"?currentpage={self.__page_no}")
            first_ad_url_tag = catalog_page.find("a", {"data-item-name": "detail-page-link"})
            if first_ad_url_tag:
                first_ad_url = TruckScout24Scraper.WEBSITE_URL + first_ad_url_tag.get("href").strip()
                page = self.__parse_page(first_ad_url)
                self.__data["ads"].append(self.__get_page_config(page, first_ad_url))
                self.__download_images(page)
                self.__page_no += 1
            else:
                break
        self.__save_json_data(self.__data, f"{self.path_to_dir}/data.json")


if __name__ == "__main__":
    truck_scout_scraper = TruckScout24Scraper("data")
    truck_scout_scraper.process()
