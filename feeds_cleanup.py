"""This script cleans up the nodes and edges CSV files by removing empty lines."""

with open('feeds/nodes.csv', 'r', encoding='utf-8') as infile, open('feeds/cleaned_nodes.csv',
                                                  'w', encoding='utf-8') as outfile:
    for line in infile:
        if line.strip() != ',':
            outfile.write(line)
    print("Nodes cleaned and saved to feeds/cleaned_nodes.csv")

with open('feeds/edges.csv', 'r', encoding='utf-8') as infile, open('feeds/cleaned_edges.csv',
                                                  'w', encoding='utf-8') as outfile:
    for line in infile:
        if line.strip() != ',':
            outfile.write(line)
    print("Edges cleaned and saved to feeds/cleaned_edges.csv")
