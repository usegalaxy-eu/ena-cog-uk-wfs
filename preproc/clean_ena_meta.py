import argparse

from collections import Counter


class ENAMetaSummary():
    def __init__(
        self, meta_in,
        filter_by_library_layout=None,
        filter_by_library_strategy=None
    ):
        self.meta_in = meta_in
        self.filter_by_library_layout = filter_by_library_layout
        self.filter_by_library_strategy = filter_by_library_strategy
        self.header = meta_in.readline()
        self.col_lookup = {
            name: idx for idx, name in enumerate(
                self.header.strip().split('\t')
            )
        }
        self.features_by_column = {
            name: Counter() for name in self.col_lookup
        }
        self.skipped_records = 0

    def __iter__(self):
        for line in self.meta_in:
            trunc_line = line.strip('\n\r')
            if trunc_line:
                self.skipped_records += 1
                fields = line.split('\t')
                if not fields[self.col_lookup['checklist']]:
                    continue
                coll_date = fields[self.col_lookup['collection_date']]
                if coll_date == '2020-01-01' or not coll_date:
                    continue

                library_layout = fields[self.col_lookup['library_layout']]
                library_strategy = fields[self.col_lookup['library_strategy']]
                link_field = fields[self.col_lookup['fastq_ftp']]
                links = link_field.split(';')
                if library_layout == 'SINGLE':
                    if len(links) != 1:
                        continue
                elif library_layout == 'PAIRED':
                    if len(links) < 2 or len(links) > 3:
                        continue
                    elif '_1' not in link_field or '_2' not in link_field:
                        continue

                # record is technically ok
                for feature in self.features_by_column:
                    self.features_by_column[feature][
                        fields[self.col_lookup[feature]]
                    ] += 1
                if self.filter_by_library_layout:
                    if library_layout != self.filter_by_library_layout:
                        continue
                if self.filter_by_library_strategy:
                    if library_strategy != self.filter_by_library_strategy:
                        continue

                # record is of a class that we want to keep
                self.skipped_records -= 1
                yield line

    @property
    def sample_count(self):
        return len(self.features_by_column['accession'])


def main(
    meta_in, meta_out,
    filter_by_library_layout=None,
    filter_by_library_strategy=None,
    mod_func=None,
    verbose=True
):
    """Call this function from importing code that defines custom modifiers."""

    s = ENAMetaSummary(meta_in, filter_by_library_layout)
    if mod_func:
        it = mod_func(s)
    else:
        it = s
        meta_out.write(s.header)
    for record_line in it:
        meta_out.write(record_line)

    if verbose:
        print('Valid samples in file:', s.sample_count)
        print('Skipped records:', s.skipped_records)
        print('Checking for duplicate samples ...', end=' ')
        duplicate_accs = [
            acc for acc, count in
            s.features_by_column['accession'].items()
            if count > 1
        ]
        if duplicate_accs:
            print('Duplicates found!')
            print('Duplicate accessions in retained records:', duplicate_accs)
        else:
            print('OK')

        print('Summary of sequencing protocols in data:')
        print('\tTypes of library layouts:')
        for layout, count in s.features_by_column['library_layout'].items():
            print(f'\t{layout}\t{count}')

        print('\tTypes of library strategies:')
        for strategy, count in s.features_by_column['library_strategy'].items():
            print(f'\t{strategy}\t{count}')

        print('\tTypes of sequencing platforms:')
        for platform, count in s.features_by_column['instrument_platform'].items():
            print(f'\t{platform}\t{count}')

        print('\tTypes of sequencer models:')
        for model, count in s.features_by_column['instrument_model'].items():
            print(f'\t{model}\t{count}')

    return s


parser = argparse.ArgumentParser()
parser.add_argument(
    'ifile',
    help='Name of the metadata input file'
)
parser.add_argument(
    '-o', '--ofile', required=True,
    help='Name of the output file'
)
parser.add_argument(
    '--ll', '--library-layout', default=None,
    help='Keep only records with this library_layout field value '
         'e.g. "SINGLE" or "PAIRED"'
)
parser.add_argument(
    '--ls', '--library-strategy', default=None,
    help='Keep only records with this library_strategy field value '
         'e.g. "AMPLICON"'
)    


if __name__ == '__main__':
    args = parser.parse_args()
    with open(args.ifile) as i, open(args.ofile, 'w') as o:
        _ = main(i, o, args.ll, args.ls)
