import sys, json
from networkx.readwrite import json_graph
import networkx as nx
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

data = json.loads(Path('graphify-out/graph.json').read_text(encoding="utf-8"))
G = json_graph.node_link_graph(data, edges='links')

question = 'license validation flow middleware crypto engine'
terms = [t.lower() for t in question.split() if len(t) > 3]

scored = []
for nid, ndata in G.nodes(data=True):
    label = ndata.get('label', '').lower()
    score = sum(1 for t in terms if t in label)
    if score > 0:
        scored.append((score, nid))
scored.sort(reverse=True)
start_nodes = [nid for _, nid in scored[:3]]

subgraph_nodes = set(start_nodes)
subgraph_edges = []
frontier = set(start_nodes)
for _ in range(3):
    next_frontier = set()
    for n in frontier:
        for neighbor in G.neighbors(n):
            if neighbor not in subgraph_nodes:
                next_frontier.add(neighbor)
                subgraph_edges.append((n, neighbor))
    subgraph_nodes.update(next_frontier)
    frontier = next_frontier

def relevance(nid):
    label = G.nodes[nid].get('label', '').lower()
    return sum(1 for t in terms if t in label)

ranked_nodes = sorted(subgraph_nodes, key=relevance, reverse=True)

lines = []
for nid in ranked_nodes:
    d = G.nodes[nid]
    src = d.get("source_file", "")
    lines.append(f'NODE {d.get("label", nid)} [src={src}]')
for u, v in subgraph_edges:
    if u in subgraph_nodes and v in subgraph_nodes:
        _raw = G[u][v]
        d = next(iter(_raw.values()), {}) if isinstance(G, nx.MultiGraph) else _raw
        lines.append(f'EDGE {G.nodes[u].get("label",u)} --{d.get("relation","")} [{d.get("confidence","")}]--> {G.nodes[v].get("label",v)}')

output = '\n'.join(lines)
Path('graphify-out/.graphify_query_result.txt').write_text(output, encoding='utf-8')
print(f'Query complete: {len(subgraph_nodes)} nodes, {len(subgraph_edges)} edges in subgraph')
print(f'Start nodes: {[G.nodes[n].get("label",n) for n in start_nodes]}')
