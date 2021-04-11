# Overview

## A collection of scripts for SARS-CoV-2 genomics analysis automation

Our automation solution comes in the form of a collection of independent small
scripts powered by the [bioblend](https://github.com/galaxyproject/bioblend)
library for interacting with the Galaxy API and by the
[workflow execution functionality](https://planemo.readthedocs.io/en/latest/running.html#workflow-execution-against-an-external-galaxy)
of the [planemo](https://github.com/galaxyproject/planemo) command-line
utilities.

## Tag-based orchestration of scripts

The actions of all scripts in the collection are controlled and coordinated via
a system of Galaxy dataset and history tags that is used to communicate input
data availability and the state of the overall analysis progress.

When run together the scripts support a fully automated SARS-CoV-2 analysis
pipeline for ARTIC paired-end sequencing data that includes

- raw sequencing data upload into Galaxy and organization of the data into dataset collections
- variant calling using our highly sensitive [published workflow for variation analysis on ARTIC PE data](https://github.com/iwc-workflows/sars-cov-2-pe-illumina-artic-variant-calling)
- generation of reports of all identified variants
- reliable consensus sequence building including soft-masking of questionable sites
- export of key analysis results - BAM files of aligned reads, VCF files of called variants, FASTA consensus sequences to a user-specific FTP folder for simplified downloading with standard FTP clients.

The full pipeline with all script actions looks like this:

1. You upload simple text files with download links for your sequencing data
   into a Galaxy history on a Galaxy server of your choice (yes, all scripts
   work on any Galaxy server you have a user account on).

   All links in one dataset will be treated as a batch of data and be analyzed
   together. Add as many datasets as you want to one or more tagged histories
   and repeated runs of the scripts will process batches one at a time.

2. You add a history tag recognized by the *variation* script, which identifies
   that history as one holding datasets with data download links that should be
   processed

3. You arrange alternating runs of the scripts and watch the automated
   batch-wise analysis of your data live in the Galaxy UI!

Learn more about:

- [Uploading and organizing download links files](./data_import.md)
- [Installation and configuration of the scripts](./manual.md)

## Contributions welcome

The current scripts support our COG-UK tracking efforts on usegalaxy.*
instances quite well, but we hope to be able to expand the collection based on
independent user, *i.e.* **your**, feedback and contributions!

Bug reports, ideas, patches, additional scripts - whatever you can provide is
very welcome!

