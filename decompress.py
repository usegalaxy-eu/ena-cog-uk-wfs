import argparse
import json

from compress_for_dashboard import parse_compressed

if __name__ == "__main__":
  ap = argparse.ArgumentParser()
  ap.add_argument("input", help="Name of the file to decompress", required=True)
  ap.add_argument("output", help="Name of the decompressed file", required=True)
  args = ap.parse_args()

  with open(args.input, "r") as in_f, open(args.output], "w") as out_f:
    compressed_data = json.load(in_f)
  
    # A row has the following columns
    # "Sample","POS","REF","ALT","AF","EFFECT","CODON","TRID","AA"
    header = "Sample\tPOS\tREF\tALT\tAF\tEFFECT\tCODON\tTRID\tAA\n"
    out_f.write(header)

    rows_gen = parse_compressed(compressed_data)
    for row in rows_gen:
      sample = row[0]
      pos, ref, alt, af, effect, codon, trid = row[1]
      aa = row[2]
      out_f.write('\t'.join([sample, str(pos), ref, alt, str(af), effect, codon, trid, aa]) + '\n'))
