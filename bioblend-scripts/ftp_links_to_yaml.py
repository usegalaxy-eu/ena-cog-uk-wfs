"""
Takes a list of ftp links and converts to a yaml file ready for upload with planemo run
"""
import argparse
import yaml

from bioblend import galaxy


WF_JOB_FILE_TEMPLATE = {'ARTIC primer BED': {'class': 'File', 'galaxy_id': '...'},
 'ARTIC primers to amplicon assignments': {'class': 'File',
  'galaxy_id': '...'},
 'FASTA sequence of SARS-CoV-2': {'class': 'File', 'galaxy_id': '...'},
 'Paired Collection (fastqsanger)': {'class': 'Collection',
  'collection_type': 'list:paired',
  'elements': []
  }}


def id_to_yaml(gi, dataset_id, output):
    links = gi.datasets.download_dataset(dataset_id).decode("utf-8").splitlines()[1:]
    wf_job_file = WF_JOB_FILE_TEMPLATE
    identifiers = set('/'.join(link.split('/')[:6]) for link in links)
    print(identifiers)
    wf_job_file['Paired Collection (fastqsanger)']['elements'] = [
        {'class': 'Collection',
            'identifier': identifier.split('/')[5],
            'type': 'paired',
            'elements': [
                {'class': 'File',
                'location': '/'.join(['ftp:/', identifier, identifier.split('/')[5] + '_1.fastq.gz']),
                'identifier': 'forward'},
                {'class': 'File',
                'location': '/'.join(['ftp:/', identifier, identifier.split('/')[5] + '_2.fastq.gz']),
                'identifier': 'reverse'}
            ]
        } for identifier in identifiers
    ]
    print(wf_job_file)
    with open(output, 'w') as f:
        f.write(yaml.dump(wf_job_file))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'dataset_id',
        help='Dataset id for download containing the FTP links'
    )
    parser.add_argument(
        '-g', '--galaxy-url', required=True,
        help='URL of the Galaxy instance to run query against'
    )
    parser.add_argument(
        '-a', '--api-key', required=True,
        help='API key to use for authenticating on the Galaxy server'
    )
    parser.add_argument(
        '-o', '--output', required=True,
        help='Output file for the job file'
    )
    args = parser.parse_args()

    gi = galaxy.GalaxyInstance(args.galaxy_url, args.api_key)
    id_to_yaml(gi, args.dataset_id, args.output)