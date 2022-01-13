import argparse
import itertools
import json
import sys

from collections import Counter


def parse_records(fh):
    for line in fh:
        line = line.strip()
        if line:
            sample, pos, ref, alt, af, eff, codon, trid, aa = line.strip(
                ).split()
            yield (
                sample,
                (int(pos), ref, alt, eff, codon, trid, aa),
                round(float(af), 4)
            )


def parse_compressed(in_json):
    triplet_value_it = (
        in_json['values'][i:i+3] for i in range(0, len(in_json['values'])-2, 3)
    )
    for sample_idx, af_idx, var_idx in triplet_value_it:
        sample = in_json['keys'][0][sample_idx]
        af = in_json['keys'][1][af_idx]
        var_idx *= 7
        var_component_idces = in_json['keys'][2][var_idx:var_idx + 7]
        variant = tuple(
            in_json['variant_keys'][n][idx] for n, idx in enumerate(
                var_component_idces
            )
        )
        yield sample, variant, af


def get_record_iterator(
    fh,
    existing_compressed=None,
    start_date=None, end_date=None
):
    if existing_compressed:
        with open(existing_compressed) as i:
            compressed_data = json.load(i)
        record_it = itertools.chain(
            parse_compressed(compressed_data),
            parse_records(fh)
        )
    else:
        record_it = parse_records(fh)
    if start_date:
        record_it = (
            rec for rec in record_it
            if sample_dates[rec[0]] >= start_date
        )
    if end_date:
        record_it = (
            rec for rec in record_it
            if sample_dates[rec[0]] <= end_date
        )
    return record_it


if __name__ == '__main__':
    arguments = argparse.ArgumentParser(
        description='Read a TSV file and compress it into a JSON with indexed '
                    'key storage. This assumes a sufficient degree of field '
                    'value repetitions.'
        )
    arguments.add_argument(
        'input',
        help='the TSV file to compress',
    )
    arguments.add_argument(
        'output',
        help='file to write the compressed JSON output to',
    )
    arguments.add_argument(
        '-u', '--use-existing',
        metavar='COMPRESSED_JSON',
        help='Append to the content of the indicated compressed JSON file. '
             'This is *not* an in-place update, but will respect the output '
             'name provided.'
        )
    arguments.add_argument(
        '-s', '--start-date',
        metavar='ISO_DATE',
        help='Only consider samples with a collection date after or equal '
             'this date during compression.\n'
             'Use --metadata-file to pass a file with collection dates of all '
             'samples.'
        )
    arguments.add_argument(
        '-e', '--end-date',
        metavar='ISO_DATE',
        help='Only consider samples with a collection date before or equal '
             'this date during compression.\n'
             'Use --metadata-file to pass a file with collection dates of all '
             'samples.'
        )
    arguments.add_argument(
        '-m', '--metadata-file',
        help='Use to specify a file with sample collection dates.\n'
             'The first two columns of this file are expected to be named '
             '"run_accession" and "collection_date" with dates in the second '
             'column specified as iso 8601 strings. Additional columns will '
             'be ignored.\n'
             'This option is required with --start-date and/or --end-date.'
        )

    # direct storage support not implemented yet!
    # arguments.add_argument(
    #     '-s', '--switch',
    #     type=float, default=10.,
    #     help ='If compression is below this cutoff, store values directly'
    # )


    args = arguments.parse_args()
    # disable direct storage of values
    args.switch = 0
    # require and read metadata file for handling dates
    if args.start_date or args.end_date:
        if not args.metadata_file:
            sys.exit(
                'A metadata file with collection dates for each sample is '
                'required with --start-date and --end-date!'
            )
        print("Reading metadata file", file=sys.stderr)
        with open(args.metadata_file) as i:
            hdr_cols = i.readline().strip().split('\t')
            if hdr_cols[:2] != ['run_accession', 'collection_date']:
                sys.exit(
                    'Expected metadata file with "run_accession" and '
                    '"collection_date" as the first two column names!'
                )
            sample_dates = {}
            for line in i:
                fields = line.strip().split('\t')
                sample_dates[fields[0]] = fields[1]

    print("Analyzing the TSV file", file=sys.stderr)
    with open (args.input, "r") as fh:
        headers = fh.readline()
        fields = [
            'sample', 'variant', 'pos', 'ref', 'alt',
            'af', 'effect', 'codon', 'trid', 'aa'
        ]
        variant_field_names = [
            'pos', 'ref', 'alt', 'effect', 'codon', 'trid', 'aa'
        ]

        per_col_unique = {
            k: Counter() for k in fields
        }
        l = 0
        record_it = get_record_iterator(
            fh, args.use_existing, args.start_date, args.end_date
        )

        for sample, variant, af in record_it:
            per_col_unique['sample'][sample] += 1
            per_col_unique['variant'][variant] += 1
            per_col_unique['af'][af] += 1
            for field_name, key in zip(variant_field_names, variant):
                per_col_unique[field_name][key] += 1
            l += 1
            if l % 50000 == 0:
                print("...Read %d lines" % l)
        print(
            "Read %d lines with %d columns" % (
                l, len(headers.strip().split('\t'))
            ),
            file = sys.stderr
        )

        # all input data read, now encode parsed values
        encoding = {}
        for field, counter in per_col_unique.items():
            if l > 0:
                ratio = l / len(counter)
                print(
                    "\tKey %s has %d unique values (%g compression)" % (
                        field, len(counter), ratio
                    ), file=sys.stderr
                )
            else:
                ratio = 1.0
            if ratio <= args.switch:
                # This branch will currently never run because the compression
                # part of the script wouldn't be able to handle it.
                per_col_unique[field] = None
                print(
                    "\t\tKey %s will be stored using direct values" % k,
                    file=sys.stderr
                )
            else:
                encoding[field] = {
                    item[0]: index for index, item in enumerate(
                        counter.most_common()
                    )
                }

    # At this point, encoding contains mappings of the form:
    # observed value in the input -> int to encode the value with
    # for every type of value extracted from the input.
    # This mapping is now used to generate the compressed JSON
    print("Compressing to JSON", file=sys.stderr)

    with open(args.input, "r") as fh:
        fh.readline()
        outputJSON = {
            'cols': headers,
            'rows': l,
            'keys': []
        }

        record_it = get_record_iterator(
            fh, args.use_existing, args.start_date, args.end_date
        )

        flat_values = []
        for sample, variant, af in record_it:
            flat_values.append(encoding['sample'][sample])
            flat_values.append(encoding['af'][af])
            flat_values.append(encoding['variant'][variant])

        variant_keys = []
        for f in variant_field_names:
            variant_keys.append(
                [k for k, v in sorted(encoding[f].items(), key=lambda x: x[1])]
            )

        variant_values = []
        for variant, n in sorted(
            encoding['variant'].items(),
            key=lambda x: x[1]
        ):
            for field_name, key in zip(variant_field_names, variant):
                variant_values.append(encoding[field_name][key])

        keys = []
        for f in ['sample', 'af']:
            keys.append(
                [k for k, v in sorted(encoding[f].items(), key=lambda x: x[1])]
            )
        # main keys contain the encoded variant values, which need to be
        # decoded through a second lookup in the variant keys.
        keys.append(variant_values)

        json_template = {
            'cols': [
                'Sample', 'POS', 'REF', 'ALT', 'AF',
                'EFFECT', 'CODON', 'TRID', 'AA'
            ],
            'rows': l,
            'variant_keys': variant_keys,
            'keys': keys,
            'values': flat_values
        }
        print(
            "Writing flat attribute values to JSON:\n"
            "%d values, %d variant values" % (
                len(flat_values), len(variant_values)
            ),
            file=sys.stderr
        )

        with open(args.output, "w") as jh:
            json.dump(json_template, jh, separators=(',', ':'))
