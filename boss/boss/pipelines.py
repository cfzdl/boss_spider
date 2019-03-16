# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import json
import csv

class BossPipeline(object):
    def __init__(self):
        self.f = open("boss.csv", "wb")


    def open_spider(self, spider):
        print("爬虫开始了！")

    def process_item(self, item, spider):
        writer = csv.writer(self.f)
        writer.writerow((item['name'], item['salary'],item['years'],item['demand'],item['address'],item['company']))
        return item

    def close_spider(self,spider):
        self.f.close()

        print('爬虫结束了...')