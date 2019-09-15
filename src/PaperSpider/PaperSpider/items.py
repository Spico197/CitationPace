# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class PaperspiderItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class Paper(scrapy.Item):
    id = scrapy.Field()
    title = scrapy.Field()
    citation_num = scrapy.Field()
    doi = scrapy.Field()
    authors = scrapy.Field()
    abstract = scrapy.Field()
    publish_year = scrapy.Field()
    # references = scrapy.Field()
    citations = scrapy.Field()
