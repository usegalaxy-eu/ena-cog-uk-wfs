import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument(
    'data_dir',
    help='Folder with BED input files arranged in by-quarter subfolders'
)
parser.add_argument(
    '-o', '--ofile', required=True,
    help='Write UCSC tracks info to this file'
)
args = parser.parse_args()

quarter_mapping = {
    'Q0': 'current quarter',
    'Q1': 'a quarter ago',
    'Q2': 'two quarters ago',
    'Q3': 'three quarters ago'
}

quarter_cols = [
    (231, 125, 99),
    (213, 78, 94),
    (169, 57, 109),
    (122, 45, 111)
]

lineage_cols = [
    (0, 28, 127),
    (177, 64, 13),
    (18, 113, 28),
    (140, 8, 0),
    (89, 30, 113),
    (89, 47, 13),
    (162, 53, 130),
    (60, 60, 60),
    (184, 133, 10),
    (0, 99, 116),
    (0, 28, 127),
    (177, 64, 13),
    (18, 113, 28),
    (140, 8, 0),
    (89, 30, 113),
    (89, 47, 13),
    (162, 53, 130),
    (60, 60, 60),
    (184, 133, 10),
    (0, 99, 116)
]

scriptdir = os.path.dirname(__file__)
print(scriptdir, os.getcwd())
longlabel = ''

with open(args.ofile, 'w') as o:
    with open(os.path.join(scriptdir, 'supertrack.txt')) as i:
        o.write(i.read())
    with open(os.path.join(scriptdir, 'quarter_template.txt')) as i:
        quarter_template = i.read()
    with open(os.path.join(scriptdir, 'lineage_template.txt')) as i:
        lineage_template = i.read()

    with os.scandir(args.data_dir) as dircontent_iter:
        quarter_folders = sorted(
            (
                content for content in dircontent_iter
                if content.is_dir() and content.name.startswith('data_')
            ),
            key=lambda x: x.name
        )
    lineage_colmap = {}
    for i, qfolder in enumerate(quarter_folders, 1):
        quarter = qfolder.name.split('_')[-1].upper()
        quarter_name = quarter_mapping[quarter]
        o.write(
            quarter_template.format(
                quarter=quarter,
                quarter_name=quarter_name,
                priority=i*10,
                rgb=','.join([str(v) for v in quarter_cols[i-1]]),
                visibility='pack' if i == 1 else 'dense'
            )
        )
        with os.scandir(qfolder) as subdircontent_iter:
            this_quarter_bedfiles = sorted(
                (
                    content for content in subdircontent_iter
                    if content.is_file() and content.name.endswith(
                        '_data.bed'
                    )
                ),
                key=lambda x: x.name
            )
        for j, bedfile in enumerate(this_quarter_bedfiles, 1):
            rank, lineage_name = bedfile.name.split('_')[:2]
            lineage = lineage_name.title().replace('.', '-')
            if lineage not in lineage_colmap:
                lineage_colmap[lineage] = lineage_cols.pop()
            with open(bedfile) as i:
                header = i.readline()
            longlabel = header.strip().replace(
                '# Mutations', 'Mutations (amino acid level)'
            )
            o.write(
                lineage_template.format(
                    quarter=quarter,
                    rank=rank,
                    priority=j*10,
                    lineage=lineage,
                    lineage_name=lineage_name,
                    longlabel=longlabel,
                    rgb=','.join([str(v) for v in lineage_colmap[lineage]])
                )
            )

