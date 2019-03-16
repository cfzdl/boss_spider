# -*- coding: utf-8 -*-
import scrapy
from boss.items import BossItem


class BossSpiderSpider(scrapy.Spider):
    name = 'boss_spider'
    allowed_domains = ['zhipin.com']
    start_urls = ['https://www.zhipin.com/c101010100-p100101/']

    def parse(self, response):
        div =  response.xpath('//div[@class="job-primary"]')
        name = div.xpath('.//div[@class="job-title"]/text()').get()
        salary = div.xpath('.//span[@class="red"]/text()').get()
        infos = div.xpath('.//p/text()').getall()
        address = infos[0]
        years = infos[1]
        demand = infos[2]
        company = div.xpath('.//div[@class="company-text"]//a/text()').get()
        items = BossItem(name=name, salary=salary, address=address, years=years, demand=demand, company=company)
        yield items
        url = response.xpath('//div[@class="page"]/a[@ka="page-next"]/@href').get()
        if url == None:
            return
        else:
            next_url = "https://www.zhipin.com" + url
            yield scrapy.Request(next_url, callback=self.parse)
