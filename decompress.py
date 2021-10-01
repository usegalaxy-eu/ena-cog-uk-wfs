import argparse
import itertools
import json

from compress_for_dashboard import parse_compressed

if __name__ == "__main__":
  ap = argparse.ArgumentParser()
  ap.add_argument("-i", "--input", help="Name of the file to decompress", required=True)
  ap.add_argument("-o", "--output", help="Name of the decompressed file", required=True)
  args =vars( ap.parse_args())

  with open(args['input'], "r") as in_f, open(args['output'], "w") as out_f:
    compressed_data = json.load(in_f)
  
    # A row has the following columns
    # "Sample","POS","REF","ALT","AF","EFFECT","CODON","TRID","AA"
    header = "Sample\tPOS\tREF\tALT\tAF\tEFFECT\tCODON\tTRID\tAA\n"
    out_f.write(header)

    rows = list(parse_compressed(compressed_data))
    for row in rows:
      sample = row[0]
      pos = row[1][0]
      ref = row[1][1]
      alt = row[1][2]
      af = row[1][3]
      effect = row[1][4]
      codon = row[1][5]
      trid = row[1][6]
      aa = row[2]
      out_f.write(str(sample) + "\t" + str(pos) + "\t" + str(ref) + "\t" + str(alt) + "\t" + str(af) + "\t" + str(effect) + "\t" + str(codon) + "\t" + str(trid) + "\t" + str(aa) + "\n")
