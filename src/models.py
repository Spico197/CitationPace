import json


class Paper(object):
    def __init__(self, **kwargs):
        # bing academic文章ID
        self.id = kwargs.get('id')
        self.title = kwargs.get('title')
        # 被引量
        self.citation_num = kwargs.get('citation_num')
        self.doi = kwargs.get('doi')
        self.authors = kwargs.get('authors')
        self.abstract = kwargs.get('abstract')
        self.publish_year = kwargs.get('publish_year')
        self.references = list()
        self.citations = list()
        self.collection_name = kwargs.get('collection_name', 'ref_cit_test_3')
        if kwargs.get('save2mongo', False):
            import pymongo

            client = pymongo.MongoClient('localhost', 27017)
            db = client['ref_cit']
            self.collection = db[self.collection_name]
            self.save_flag = 'mongo'
        else:
            self.save_flag = 'json'
    def save(self):
        data = {
            'id': self.id,
            'title': self.title,
            'citation_num': int(self.citation_num),
            'doi': self.doi,
            'authors': self.authors,
            'abstract': self.abstract,
            'publish_year': int(self.publish_year),
            'references': self.references,
            'citations': self.citations, 
        }
        if self.save_flag == 'mongo':
            if self.collection.find({"id": self.id}).count() <= 0:
                self.collection.insert_one(data)
        else:
            with open(self.collection_name, 'a') as f:
                f.write('{}\n'.format(json.dumps(data, ensure_ascii=False)))

    def __str__(self):
        return_string = "<Paper: { "
        for key, value in self.__dict__.items():
            return_string += '{}:"{}", '.format(key, value)
        return_string = return_string[:-2]
        return_string += ' }>'
        return return_string
