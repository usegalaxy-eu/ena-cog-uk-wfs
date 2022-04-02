"""Gathers information from three input files -
a tabular file with per-sample variant information,
a tabular file with pangolin lineage information, and
a JSON file with sample and batch metadata.
"""

import argparse
import gzip
import heapq
import json
import os
import statistics
import sys

class SampleSummary():
    def __init__(self, batched_sample_dict):
        sample_info = {}
        for sample, batch in self.get_sample_batch_assocs(
            batched_sample_dict
        ).items():
            sample_info[sample] = {
                'batch': batch,
                'study_accession': batched_sample_dict[batch]['study_accession'],
                'collection_date': batched_sample_dict[batch][
                    'collection_dates'
                    ][batched_sample_dict[batch]['samples'].index(sample)
                ]
            }
        self.summary = sample_info

    def update_sample(self, sample, sample_info):
        self.summary[sample].update(sample_info)

    def __getitem__(self, sample):
        return self.summary[sample]

    def keys(self):
        return self.summary.keys()

    def values(self):
        return self.summary.values()

    def items(self):
        return self.summary.items()

    def get(self, sample, default=None):
        return self.summary.get(sample, default)

    def __len__(self):
        return len(self.summary)

    def get_sample_batch_assocs(self, batched_sample_dict):
        assocs = {}
        for batch, batch_data in batched_sample_dict.items():
            for sample in batch_data['samples']:
                if sample in assocs:
                    new_data_comp = (
                        batch_data['variation']['workflow_version'],
                        batch_data['report']['workflow_version'],
                        batch_data['consensus']['workflow_version'],
                        batch_data['time']
                    )
                    current_data = batched_sample_dict[assocs[sample]]
                    current_data_comp = (
                        current_data['variation']['workflow_version'],
                        current_data['report']['workflow_version'],
                        current_data['consensus']['workflow_version'],
                        current_data['time']
                    )
                    if new_data_comp < current_data_comp:
                        # the batch that this sample is currently associated
                        # with represents a newer analysis than the incoming
                        # batch => leave associations alone
                        continue
                assocs[sample] = batch
        return assocs


class LineageSummary():
    def __init__(self, sample_records, start_date, end_date):
        lineage_dict = {}
        for record in sample_records:
            lineage = record['lineage']
            if not lineage:
                continue
            coll_date = record.get('collection_date')
            if coll_date < '2020-01-04':
                # exclude samples with unplausible collection dates
                continue
            in_date_range = (
                not start_date or start_date <= coll_date
            ) and (
                not end_date or coll_date < end_date
            )
            if lineage not in lineage_dict:
                lineage_dict[lineage] = {
                    'total_samples': 1 if in_date_range else 0,
                    'variants': {},
                    'first_seen': coll_date,
                    'last_seen': coll_date
                }
            else:
                if in_date_range:
                    lineage_dict[lineage]['total_samples'] += 1
                if (
                    not lineage_dict[lineage]['first_seen']
                ) or (coll_date < lineage_dict[lineage]['first_seen']):
                    lineage_dict[lineage]['first_seen'] = coll_date
                if (
                    not lineage_dict[lineage]['last_seen']
                ) or (coll_date > lineage_dict[lineage]['last_seen']):
                    lineage_dict[lineage]['last_seen'] = coll_date

        self.summary = {
            k: v for k, v in lineage_dict.items() if v['total_samples'] > 0
        }

    def most_common(self, n):
        return {
            k: v for k, v in sorted(
                self.summary.items(),
                key=lambda x: x[1]['total_samples'],
                reverse=True
            )[:n]
        }
    
    def __getitem__(self, lineage):
        return self.summary[lineage]

    def keys(self):
        return self.summary.keys()

    def values(self):
        return self.summary.values()

    def items(self):
        return self.summary.items()


def add_lineage_info(sample_summary, lineage_records):
    for line in lineage_records:
        fields = line.strip().split('\t')[:5]
        accession, lineage, scorpio_call = fields[0], fields[1], fields[4]
        sample_info = sample_summary.get(accession)
        if sample_info:
            if 'lineage' in sample_info or 'scorpio_call' in sample_info:
                print(
                    'Duplicate pangolin output found for: {0}'.format(
                        accession
                    ), file=sys.stderr
                )
            else:
                sample_summary.update_sample(
                    accession,
                    {'lineage': lineage, 'scorpio_call': scorpio_call}
                )


def parse_variant_records(variants_in):
    hdr = variants_in.readline().strip().split('\t')
    for line in variants_in:
        data = {k: v for k, v in zip(hdr, line.strip().split('\t'))}
        yield data.pop('Sample'), data.pop('Batch'), data


parser = argparse.ArgumentParser()
parser.add_argument(
    '-m', '--metadata_fn', required=True,
    help='Path to metadata JSON file'
)
parser.add_argument(
    '-l', '--lineage_fn', required=True,
    help='Path to lineage assignment file'
)
parser.add_argument(
    '-v', '--variants_fn', required=True,
    help='Path to tabular variants file'
)
parser.add_argument(
    '-o', '--outdir', required=True,
    help='Name of output folder'
)
parser.add_argument(
    '-f', '--var-freq-threshold', type=float, default=0.001,
    help='Minimal frequency with which a variant has to occur in a lineage '
         'to be reported for that lineage'
)
parser.add_argument(
    '-n', '--n-lineages', type=int, default=20,
    help='Report the n lineages most represented in the data (default: 20)'
)
parser.add_argument(
    '-s', '--start-date', default=None,
    metavar='ISO_DATE',
    help='Only consider samples with a collection date after or equal this date.'
)
parser.add_argument(
    '-e', '--end-date', default=None,
    metavar='ISO_DATE',
    help='Only consider samples with a collection date before this date.'
)
args = parser.parse_args()
outdir = args.outdir

if not os.path.isdir(outdir):
    os.makedirs(outdir)

project_country_map = {
    'PRJEB37886': 'GB',
    'PRJEB40277': 'IE',
    'PRJEB44141': 'GR',
    'PRJNA636748': 'ZA',
}
default_country = 'EE'


print('Parsing known samples metadata ...', file=sys.stderr)
sample_info = SampleSummary(json.load(open(args.metadata_fn)))
print(
    'Read metadata for {0} samples.'.format(len(sample_info)),
    file=sys.stderr
)

print('Reading pangolin lineage information ...', file=sys.stderr)
with gzip.open(args.lineage_fn, 'rt') as pango_in:
    header = pango_in.readline().strip().split('\t')
    assert header[:5] == [
        'taxon', 'lineage', 'conflict', 'ambiguity_score', 'scorpio_call'
    ], "This doesn't look like the expected pangolin output format"

    add_lineage_info(sample_info, pango_in)

records_with_lineages = {
    k: v for k, v in sample_info.items()
    if v.get('lineage') and v['lineage'] != 'None'
}
print(
    'Lineage assignments found for {0} samples'
    .format(len(records_with_lineages)),
    file=sys.stderr
)

lineage_dict = LineageSummary(
    records_with_lineages.values(), args.start_date, args.end_date
).most_common(args.n_lineages)

print(lineage_dict, file=sys.stderr)

print('Parsing per-sample variants data ...', file=sys.stderr)
variant_effects = {}
with gzip.open(args.variants_fn, 'rt') as variants_in:
    for sample, batch, variant_data in parse_variant_records(variants_in):
        if (sample in records_with_lineages) and (
            records_with_lineages[sample]['batch'] == batch
        ):
            lineage = records_with_lineages[sample]['lineage']
            if lineage in lineage_dict:
                country = project_country_map.get(
                    records_with_lineages[sample]['study_accession'],
                    default_country
                )
                coll_date = records_with_lineages[sample]['collection_date']
                if coll_date < '2020-01-04':
                    # exclude samples with unplausible collection dates
                    continue

                lineage_variants = lineage_dict[lineage]['variants']
                variant = (
                    int(variant_data['POS']),
                    variant_data['REF'],
                    variant_data['ALT']
                )
                variant_effects[variant] = {
                    k: variant_data[k] for k in [
                        'EFFECT', 'CODON', 'AA', 'TRID'
                    ]
                }
                if variant not in lineage_variants:
                    lineage_variants[variant] = {
                        'AFs': [],
                        'countries': set(),
                        'first_seen': coll_date
                    }
                if coll_date <= lineage_variants[variant]['first_seen']:
                    lineage_variants[variant]['first_seen'] = coll_date
                    lineage_variants[variant]['first_seen_sample'] = sample
                    lineage_variants[variant]['first_seen_in'] = country
                if (
                    not args.start_date or args.start_date <= coll_date
                ) and (
                    not args.end_date or coll_date < args.end_date
                ):
                    lineage_variants[variant]['AFs'].append(float(variant_data['AF']))
                    lineage_variants[variant]['countries'].add(country)


# clean sample info to retain only samples with a recorded collection date,
# which also have been lineage-assigned successfully.
# Assignment can either fail ("None" case) or may not have been attempted
# yet ('' case) if the fasta file of the sample hasn't been exported yet
# sample_info = {
#     k: v for k, v in sample_info.items()
#     if v[0] and v[0] != '2020-01-01' and v[2] and v[2] != 'None'
# }


print('Generating per-lineage data tables ...', file=sys.stderr)

if args.start_date:
    if args.end_date:
        header_suffix = 'between {0} and {1}'.format(
            args.start_date, args.end_date
        )
    else:
        header_suffix = 'between {0} and '.format(args.start_date)
elif args.end_date:
    header_suffix = 'until {0}'.format(args.end_date)
else:
    header_suffix = ''

for n, lineage_data in enumerate(lineage_dict.items()):
    lineage, data = lineage_data
    if args.start_date and not args.end_date:
        # If a start but no end date has been given, record the
        # collection date of the most recent sample of the lineage in the
        # header.
        lineage_header_suffix = header_suffix + data['last_seen']
    else:
        lineage_header_suffix = header_suffix
    ofile = os.path.join(
        outdir,
        '{0:02d}_{1}_data.bed'.format(n, lineage)
    )
    heap_buffer = []
    with open(ofile, 'w') as plain_tabular:
        print(
            '# Mutations in',
            lineage,
            lineage_header_suffix,
            file=plain_tabular
        )
        for variant, variant_data in sorted(
            data['variants'].items(), key=lambda x: x[0]
        ):
            variant_lineage_frequency = len(variant_data['AFs']) / data['total_samples']
            if variant_lineage_frequency < args.var_freq_threshold:
                continue
            if len(variant_data['AFs']) >= 2:
                af_q25, af_median, af_q75 = statistics.quantiles(variant_data['AFs'])
            else:
                af_q25, af_median, af_q75 = float('nan'), variant_data['AFs'][0], float('nan')
            if len(variant[1]) == 1:
                if len(variant[2]) == 1:
                    # a SNV
                    thick_start = variant[0] - 1
                    thick_end = thick_start + 1
                    if variant_effects[variant]['CODON'] == '.':
                        # not a coding change
                        chrom_start = thick_start
                        chrom_end = thick_end
                    else:
                        # mark the coding triplet as affected
                        offset = variant_effects[variant]['CODON'].index(variant[1])
                        chrom_start = thick_start - offset
                        chrom_end = chrom_start + 3
                else:
                    # an insertion or a combined SNV + insertion
                    # a simple insertion has no thick part
                    # the combined case has a thick representation because
                    # of its SNV
                    offset = 0 if variant[1] == variant[2][0] else -1
                    thick_start = chrom_start = variant[0] + offset
                    chrom_end = chrom_start + 1
                    thick_end = chrom_start - offset
            else:
                if len(variant[2]) == 1:
                    # a deletion or a combined SNV + deletion
                    # all deletions have completely thick representations
                    # cause the extent of their effects beyond the nuc level
                    # is too hard to predict
                    offset = 0 if variant[2] == variant[1][0] else -1
                    thick_start = chrom_start = variant[0] + offset
                    thick_end = chrom_end = chrom_start + len(variant[1]) - 1 - offset
                else:
                    # some complex change
                    # don't do anything clever at the moment
                    # (assuming that this is a plain MNV)
                    # TO DO: think about handling this better
                    thick_start = chrom_start = variant[0] - 1
                    thick_end = chrom_end = chrom_start + len(variant[1])

            line_to_write = 'NC_045512v2\t{}\t{}\t{}\t{}\t+\t{}\t{}\t{}/{}\t{}\t{}\t'.format(
                chrom_start,
                chrom_end,
                variant_effects[variant]['AA'], # use AA as feature name
                int(variant_lineage_frequency * 1000), # score
                thick_start,
                thick_end,
                variant[1], variant[2],
                variant_effects[variant]['EFFECT'],
                variant_effects[variant]['TRID'],
            )
            line_to_write += '{:.2f}\t{:.2f}\t{:.2f}\t{}\t{:.3f}\t{}\t{}\t{}\t'.format(
                af_median, af_q25, af_q75,
                lineage,
                variant_lineage_frequency,
                variant_data['first_seen'],
                variant_data['first_seen_sample'],
                variant_data['first_seen_in']
            )
            line_to_write += ','.join(sorted(variant_data['countries']))

            if not heap_buffer or heap_buffer[0][0] + 3 >= chrom_start:
                heapq.heappush(
                    heap_buffer,
                    (chrom_start, line_to_write)
                )
                continue
            chrom_start, line_to_write = heapq.heapreplace(
                heap_buffer,
                (chrom_start, line_to_write)
            )

            print(line_to_write, file=plain_tabular)

        while heap_buffer:
            chrom_start, line_to_write = heapq.heappop(
                heap_buffer
            )
            print(line_to_write, file=plain_tabular)

#            plain_tabular.write(
#                # $chromStart $gene:$name $codonChange Lineage Frequency: $withinLineageFrequency Intrasample AF: $medianAF ($q25AF - $q75AF)
#                '{} {}:{} {} Lineage Frequency: {:.2f} Intrasample AF: {:.2f} ({:.2f} - {:.2f})\n'
#                .format(
#                    variant[0] - 1,
#                    variant[5],
#                    variant[6],
#                    variant[4],
#                    variant_lineage_frequency,
#                    af_median, af_q25, af_q75
#                )
#            )

# for file in $(find test99/ -maxdepth 1 -type f); do bedToBigBed -type=bed5+13 -as=highQualityVariants.as -tab $file wuhCor1.chrom.sizes test99/bb/$(basename $file .bed).bb; done
