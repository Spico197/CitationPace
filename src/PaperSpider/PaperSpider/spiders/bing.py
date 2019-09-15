# -*- coding: utf-8 -*-
import re
from urllib.parse import unquote

import requests
import scrapy
from scrapy.utils.project import get_project_settings
from lxml import etree

from PaperSpider.items import Paper

settings = get_project_settings()


class BingSpider(scrapy.Spider):
    name = 'bing'
    allowed_domains = ['cn.bing.com']
    start_urls = ['http://cn.bing.com/']
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Safari/537.36',
        'accept-language': 'zh-CN,zh;q=0.9'
    }
    base = 'https://cn.bing.com'
    start_url = 'https://cn.bing.com/academic/profile?id={}&encoded=0&v=paper_preview&mkt=zh-cn'

    def start_requests(self):
        start_id = settings.get('START_ID')
        start_url = self.start_url.format(start_id)
        yield scrapy.Request(start_url, headers=self.headers, callback=self.parse, meta={'id': start_id})

    def parse(self, response):
        paper = Paper()
        
        result = re.search(r'IG:"(.*?)"', response.text)
        if result:
            ig = result.group(1)
        result = re.search(r'被 引 量</span></span><span class="aca_content"><div>(\d*)</div>', response.text)
        if result:
            paper['citation_num'] = result.group(1)
        else:
            paper['citation_num'] = 0
        paper['title'] = response.xpath('//li[@class="aca_title"]/text()').extract_first()
        paper['id'] = response.meta['id']
        result = re.search(r'<span class="aca_label">DOI</span></span><span class="aca_content"><div>(.*?)</div>', response.text)
        if result:
            paper['doi'] = result.group(1)    
        paper['authors'] = response.xpath('//div[@class="aca_desc b_snippet"]/span//a/text()').extract()
        abstract = response.xpath('//div[@class="aca_desc b_snippet"]/span[1]//text()').extract()
        if abstract:
            paper['abstract'] = abstract[-1]
        result = re.search(r'<span class="aca_label">发表日期</span></span><span class="aca_content"><div>(\d*)</div>', response.text)
        if result:
            paper['publish_year'] = result.group(1)

        base_url = 'https://cn.bing.com/academic/papers?ajax=scroll&infscroll=1&id={id}&encoded=0&v=paper_preview&mkt=zh-cn&first={first}&count={count}&IG={ig}&IID=morepage.{num}&SFX={num}&rt={rt}'
        
        count = 9
        citation_links = list()
        for i in range(1, int(paper['citation_num'])//count):
            ajax_url = base_url.format(id=paper['id'], first=i*(count+1), count=count+1, ig=ig, num=i, rt='2')
            links = self._parse_links(ajax_url)
            citation_links.extend(links)
        
        # ref_links = list()
        # for i in range(1, int(paper['citation_num'])//count):
        #     ajax_url = base_url.format(id=paper['id'], first=i*(count+1), count=count+1, ig=ig, num=i, rt='1')
        #     links = self._parse_links(ajax_url)
        #     ref_links.extend(links)

        # references = list()
        # if len(ref_links) >= 0:
        #     for ref_link in ref_links:
        #         ref_link = self.base + ref_link
        #         obj = re.search(r'search\?q=(.*?)&mkt=zh-cn', ref_link)
        #         if obj:
        #             # TODO: references analysis to be supported
        #             profile_id = self._parse_id(ref_link, self.title_normalize(obj.group(1).replace('+', ' ')))
        #             references.append({'title': obj.group(1).replace('+', ' '), 'profile_id': profile_id})
        #             # if profile_id:
        #             #     references.append(profile_id)
        #             #     yield scrapy.Request(self.start_url.format(profile_id), headers=self.headers, callback=self.parse, meta={'id': profile_id})
        # references = list()

        # paper['references'] = references

        citations = list()
        if len(citation_links) >= 0:
            for citation_link in citation_links:
                citation_link = self.base + citation_link
                obj = re.search(r'search\?q=(.*?)&mkt=zh-cn', citation_link)
                if obj:
                    profile_id = self._parse_id(citation_link, self.title_normalize(obj.group(1).replace('+', ' ')))
                    if profile_id:
                        citations.append({'title': obj.group(1).replace('+', ' '), 'profile_id': profile_id})
                        yield scrapy.Request(self.start_url.format(profile_id), headers=self.headers, callback=self.parse, meta={'id': profile_id})
        paper['citations'] = citations
        
        yield paper

    def httpget(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=10.0)
            response.raise_for_status()
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            print(e)
            return etree.HTML('<html></html>')
        return etree.HTML(response.text)

    def _parse_links(self, url):
        response = self.httpget(url)
        return response.xpath('//a[@target="_blank"]/@href')

    def _parse_id(self, url, title):
        response = self.httpget(url)
        if self.title_normalize(''.join(response.xpath('//*[@id="b_results"]/li[1]/h2/a/strong/text()'))) != title:
            return False
        else:
            href = response.xpath('//*[@id="b_results"]/li[1]/h2/a/@href')[0]
            result = re.search(r'id=(.*?)&', href)
            if result:
                return result.group(1)
            else:
                return False

    def title_normalize(self, title):
        ascii_set = set('abcdefghijklmnopqrstuvwxyz')
        new_title = ""
        title = unquote(title)
        for c in title:
            if c.lower() in ascii_set:
                new_title += c.lower()
        return new_title
