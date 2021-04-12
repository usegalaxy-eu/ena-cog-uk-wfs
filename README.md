# Bots for SARS-CoV-2 genome surveillance

If you have to analyze a huge number of SARS-CoV-2 sequences on a regular
basis, you will probably want to automate the excution of the analysis.

In particular, you may be looking for:

- an automated way to upload newly available data into Galaxy and arrange it into collections
  
- trigger execution of your variation analysis workflow, and proceed with downstream workflows for consensus building and reporting as soon as the variation workflow finishes

- arrange the workflow results into batch-specific histories

Here you find the solution used by usegalaxy.* instances to track National
Genome Surveillance projects, like COG-UK, and reanalyze their data as it
becomes publicly available.

Our automation scripts can be combined with any scheduling system and allow us
to achieve a daily throughput of more than 1,000 samples on any individual
usegalaxy.* instance with minimal impact on the analysis needs of our users.

You can use these scripts with little or no modifications to automate your own
SARS-CoV-2 analyses on a public server or your own instance of Galaxy.

Interested? Then [read on ...](docs/overview.md)
