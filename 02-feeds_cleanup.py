import csv

with open('feeds/nodes.csv', 'r') as infile, open('feeds/cleaned_nodes.csv',
                                                  'w+') as outfile:
    for line in infile:
        if line.strip() != ',':
            outfile.write(line)
    print("Nodes cleaned and saved to feeds/cleaned_nodes.csv")

with open('feeds/edges.csv', 'r') as infile, open('feeds/cleaned_edges.csv',
                                                  'w+') as outfile:
    for line in infile:
        if line.strip() != ',':
            outfile.write(line)
    print("Edges cleaned and saved to feeds/cleaned_edges.csv")
