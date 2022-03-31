import sys

with open(sys.argv[1]) as i:
    # echo stripped header line
    print('\t'.join(i.readline().split('\t')[:3]))

    # deduplicate sample lines
    seen = set()

    for line in i:
        sample, coll_date, comp_date = line.split('\t')[:3]
        if sample not in seen:
            seen.add(sample)
            print(sample, coll_date, comp_date, sep='\t')
