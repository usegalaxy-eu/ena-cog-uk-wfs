import argparse
import json

from compress_for_dashboard import parse_compressed

if __name__ == "__main__":
  ap = argparse.ArgumentParser()
  ap.add_argument("input", help="Name of the file to decompress")
  ap.add_argument("output", help="Name of the decompressed file")
  args = ap.parse_args()

  with open(args.input, "r") as in_f, open(args.output, "w") as out_f:
    compressed_data = json.load(in_f)

    # A row has the following columns
    # "Sample","POS","REF","ALT","EFFECT","CODON","TRID","AA","AF"
    header = "Sample\tPOS\tREF\tALT\tEFFECT\tCODON\tTRID\tAA\tAF\n"
    out_f.write(header)

    rows_gen = parse_compressed(compressed_data)
    for row in rows_gen:
      sample = row[0]
      pos, ref, alt, effect, codon, trid, aa = row[1]
      af = row[2]
      out_f.write('\t'.join([sample, str(pos), ref, alt, effect, codon, trid, str(aa), str(af)]) + '\n')
