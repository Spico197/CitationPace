import io
import sys
import re
import time
from urllib.parse import unquote

import requests
from lxml import etree

from models import Paper


link2id = dict()
MONGO = True
if MONGO:
    import pymongo
    client = pymongo.MongoClient()
    db = client['ref_cit']
    data_collection = db['ref_cit_test_4']
    link2id_collection = db['link2id']


def title_normalize(title):
    ascii_set = set('abcdefghijklmnopqrstuvwxyz')
    new_title = ""
    title = unquote(title)
    for c in title:
        if c.lower() in ascii_set:
            new_title += c.lower()
    return new_title


def get_profile_id(link):
    obj = re.search(r'search\?q=(.*?)&mkt=zh-cn', link)
    if obj:
        # 先从citation url中获取真正参考文献的标题信息
        original_title = obj.group(1).replace('+', ' ')
        title = title_normalize(original_title)
        if MONGO:
            if link2id_collection.find({"link": link}).count() > 0:
                data = link2id_collection.find({"link": link})[0]
                return {"title": original_title, "profile_id": data["profile_id"]}
        else:
            if link in link2id:
                return {'title': original_title, 'profile_id': link2id[link]}
    else:
        return {'title': None, 'profile_id': None}
    base_url = 'https://cn.bing.com'
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Safari/537.36',
        'accept-language': 'zh-CN,zh;q=0.9'
    }
    while True:
        try:
            response = requests.get(base_url + link, headers=headers, timeout=3.0)
            break
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            print(e)

    response.raise_for_status()
    html = etree.HTML(response.text) # html为搜索结果
    try:
        # 如果第一个搜索结果和真实标题不一致，舍弃
        if title_normalize(''.join(html.xpath('//*[@id="b_results"]/li[1]/h2/a/strong/text()'))) != title:
            return {'title': original_title, 'profile_id': None}
        else:
            # 如果一致，获取url中的id信息
            href = html.xpath('//*[@id="b_results"]/li[1]/h2/a/@href')[0]
            result = re.search(r'id=(.*?)&', href)
            if result:
                if MONGO:
                    link2id_collection.insert_one({"link": link, "profile_id": result.group(1)})
                else:
                    link2id[link] = result.group(1)
                return {'title': original_title, 'profile_id': result.group(1)}
            else:
                return {'title': original_title, 'profile_id': None}
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except Exception as e:
        return {'title': original_title, 'profile_id': None}


def get_references_citations_by_id(profile_id):
    if isinstance(profile_id, dict):
        profile_id = profile_id.get('profile_id')
        if MONGO:
            if data_collection.find({"id": profile_id}).count() > 0:
                # 说明这个数据已经被爬取过了
                return []
    print('func2')
    if not profile_id:
        return -1
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Safari/537.36',
        'accept-language': 'zh-CN,zh;q=0.9'
    }
    session = requests.Session()
    while True:
        try:
            response = session.get('https://cn.bing.com/academic/profile?id={}&encoded=0&v=paper_preview&mkt=zh-cn'.format(profile_id), headers=headers)
            response.raise_for_status()
            response.encoding = 'utf-8'
            break
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            time.sleep(3.0)
            print(e)    
    result = re.search(r'IG:"(.*?)"', response.text)
    if result:
        ig = result.group(1)
    result = re.search(r'被 引 量</span></span><span class="aca_content"><div>(\d*)</div>', response.text)
    if result:
        citation_num = result.group(1)

    html = etree.HTML(response.text)

    paper = Paper(save2mongo=MONGO)
    try:
        paper.title = html.xpath('//li[@class="aca_title"]/text()')[0]
        paper.id = profile_id
        paper.citation_num = citation_num
        result = re.search(r'<span class="aca_label">DOI</span></span><span class="aca_content"><div>(.*?)</div>', response.text)
        if result:
            paper.doi = result.group(1)    
        paper.authors = html.xpath('//div[@class="aca_desc b_snippet"]/span//a/text()')
        paper.abstract = html.xpath('//div[@class="aca_desc b_snippet"]/span[1]//text()')[-1]
        result = re.search(r'<span class="aca_label">发表日期</span></span><span class="aca_content"><div>(\d*)</div>', response.text)
        if result:
            paper.publish_year = result.group(1)

        base_url = 'https://cn.bing.com/academic/papers?ajax=scroll&infscroll=1&id={id}&encoded=0&v=paper_preview&mkt=zh-cn&first={first}&count={count}&IG={ig}&IID=morepage.{num}&SFX={num}&rt={rt}'
        
        count = 9
        citation_links = list()
        for i in range(1, int(citation_num)//count):
            ajax_url = base_url.format(id=profile_id, first=i*(count+1), count=count+1, ig=ig, num=i, rt='2')
            while True:
                try:
                    response = session.get(ajax_url, headers=headers)
                    response.raise_for_status()
                    response.encoding = 'utf-8'
                    break
                except KeyboardInterrupt:
                    raise KeyboardInterrupt
                except Exception as e:
                    time.sleep(3.0)
                    print(e) 
            html = etree.HTML(response.text)
            citation_links.extend(html.xpath('//a[@target="_blank"]/@href'))
        print('number of citation_links', len(citation_links), 'citation_num', citation_num)
        if len(citation_links) >= 0:
            for i, citation_link in enumerate(citation_links):
                profile_id = get_profile_id(citation_link)
                if profile_id.get('title', False):
                    paper.citations.append(profile_id)
                print('get_profile_id: {}/{}\r'.format(i+1, len(citation_links)), end='')
        print('\nnumber of ids:', len(paper.citations))
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except Exception as e:
        print(e)
    paper.save()
    # for profile_id in paper.citations:
    #     get_references_citations_by_id(profile_id)
    return paper.citations
    # ref_links = list()
    # for i in range(1, int(citation_num)//count):
    #     ajax_url = base_url.format(id=profile_id, first=i*(count+1), count=count+1, ig=ig, num=i, rt='1')
    #     response = session.get(ajax_url)
    #     response.raise_for_status()
    #     html = etree.HTML(response.text)
    #     ref_links.extend(html.xpath('//a[@target="_blank"]/@href'))
    # print('number of ref_links', len(ref_links))
    # if len(ref_links) >= 0:
    #     for ref_link in ref_links:
    #         profile_id = get_profile_id(ref_link)
    #         paper.references.append(get_references_citations_by_id(profile_id))
    

if __name__ == "__main__":
    # sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='gb18030')

    print('Started')
    ids = get_references_citations_by_id('63e64c6d011b61bb6b6b473c98555bb5')
    while len(ids) > 0:
        id_t = list()
        for id in ids:
            ids_new = get_references_citations_by_id(id)
            if isinstance(ids_new, list):
                id_t.extend(ids_new)
        ids = id_t

    import json
    with open('link2id.json', 'w') as fo:
        json.dump(link2id, fo)
