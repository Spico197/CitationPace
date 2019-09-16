import pdb
import pymongo
import networkx as nx
import matplotlib.pyplot as plt

client = pymongo.MongoClient()
db = client['ref_cit']
collection = db['ref_cit_test_3']
data = list(collection.find({"title": {"$regex":"elation"}}))


nodes  = list()
for x in data:
    nodes.append(x.get('id'))

profileid2title = dict()

edges = list()
for x in data:
    # 对于每一条数据来说，取该数据的后继节点
    citations = x.get('citations')
    for c in citations:
        if c.get('profile_id'):
            if 'elation' in c.get('title'):
                profileid2title[c.get('profile_id')] = c.get('title')
                if c.get('profile_id') not in nodes:
                    nodes.append(c.get('profile_id'))
                t = (x.get('id'), c.get('profile_id'))
                edges.append(t)

G = nx.DiGraph()
G.add_nodes_from(nodes)
G.add_edges_from(edges)

# try:
#     assert G.number_of_nodes() == len(nodes)
#     assert G.number_of_edges() == len(edges)
# except KeyboardInterrupt:
#     raise KeyboardInterrupt
# except Exception as e:
#     print(e)
#     pdb.set_trace()
    
node_sizes = list()
labels = list()
for node in nodes:
    if collection.find({"id": node}).count() <= 0:
        # node not in data collection
        node_sizes.append(1)
        labels.append(profileid2title[node])
    else:
        d = collection.find_one({"id": node})
        node_sizes.append(int(d.get("citation_num", 1)))
        labels.append(d.get('title', 'NULL'))
labels = {node: label for node, label in zip(nodes, labels)}

max_node_sizes = max(node_sizes)
min_node_sizes = min(node_sizes)
node_sizes = [(x - min_node_sizes)/(max_node_sizes - min_node_sizes)*600.0 for x in node_sizes]

fig = plt.figure(dpi=300)
fig.set_size_inches(80.0, 45.0) 
nx.draw(G, pos=nx.spring_layout(G), node_size=node_sizes, labels=labels, 
        node_color='r', edge_color='k',
        with_labels=True, arrow_size=50, font_size=10, font_color='b')
plt.savefig("path_new.pdf", format='pdf', dpi='figure')
# plt.show()
