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


if __name__ == '__main__':
    arguments = argparse.ArgumentParser(
        description='Read a TSV file and compress it into a JSON with indexed '
                    'key storage. This assumes a sufficient degree of field '
                    'value repetitions.'
        )
    arguments.add_argument(
        'input',
        help='The TSV file to compress',
    )
    arguments.add_argument(
        'output',
        help='The JSON file to compress the input file to',
    )
    arguments.add_argument(
        '-u', '--use-existing',
        help='Update the indicated compressed JSON file. This is *not* an '
             'in-place update, but will respect the output name provided.'
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


    print ("Analyzing the TSV file", file = sys.stderr)
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
        if args.use_existing:
            with open(args.use_existing) as i:
                compressed_data = json.load(i)
            record_it = itertools.chain(
                parse_compressed(compressed_data),
                parse_records(fh)
            )
        else:
            record_it = parse_records(fh)
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

        for k, v in per_col_unique.items():
            ratio = l / len(v)
            print(
                "\tKey %s has %d unique values (%g compression)" % (
                    k, len(v), ratio
                ), file=sys.stderr
            )
            if ratio <= args.switch:
                # This branch will currently never run because the compression
                # part of the script wouldn't be able to handle it.
                per_col_unique[k] = None
                print(
                    "\t\tKey %s will be stored using direct values" % k,
                    file=sys.stderr
                )
            else:
                encoding = {}
                for f in fields:
                    encoding[f] = {
                        k: index for index, k in enumerate(
                            sorted(
                                per_col_unique[f],
                                key=lambda x: per_col_unique[f][x],
                                reverse=True
                            )
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

        if args.use_existing:
            record_it = itertools.chain(
                parse_compressed(compressed_data),
                parse_records(fh)
            )
        else:
            record_it = parse_records(fh)

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
