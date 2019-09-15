# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import pymongo
from scrapy.utils.project import get_project_settings

settings = get_project_settings()


class PaperspiderPipeline(object):
    def __init__(self):
        self.client = pymongo.MongoClient(settings['MONGO_HOST'], settings['MONGO_PORT'])
        self.db = self.client[settings['MONGO_DB']]
        self.collection = self.db[settings['MONGO_COLLECTION']]

    def process_item(self, item, spider):
        if self.collection.find({'id': item['id']}).count() <= 0:
            self.collection.insert_one(dict(item))
            return item
