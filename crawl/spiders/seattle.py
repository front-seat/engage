import scrapy


class SeattleSpider(scrapy.Spider):
    name = "seattle"
    allowed_domains = ["seattle.legistar.com"]
    start_urls = ["https://seattle.legistar.com"]

    def parse(self, response):
        pass
