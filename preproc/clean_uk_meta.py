import clean_ena_meta


def prepend_batch_id(s):
    yield 'batch_id\t' + s.header
    for record_line in s:
        run_alias = record_line.split('\t')[s.col_lookup['library_name']]
        batch_id = run_alias.partition(' / ')[0]
        if batch_id:
            yield batch_id + '\t' + record_line

if __name__ == '__main__':
    args = clean_ena_meta.parser.parse_args()

    with open(args.ifile) as i, open(args.ofile, 'w') as o:
        _ = clean_ena_meta.main(i, o, args.ll, mod_func=prepend_batch_id)
