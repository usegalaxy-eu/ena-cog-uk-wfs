## Usage instructions for SARS-CoV-2 variation analysis automation scripts

### Getting the code and installing requirements

1. Git clone or download the code from

   https://github.com/simonbray/ena-cog-uk-wfs

2. Install a suitable version of [planemo](https://planemo.readthedocs.io)

   1. Create a Python virtual environment for the installation via:

      `python3 -m venv planemo_sars-cov2`

      Run this command inside the cloned/downloaded folder if you want to keep
      everything in one place.

   2. Activate the virtual environment:

      `. planemo_sars-cov2/bin/activate`

   3. Install planemo into the environment with:

      `pip install -r requirements.txt`

   4. That's it!

      At this point you can deactivate the virtual environment until you run
      the first automation script. Simply run `deactivate` to do so.

### Configuration

Each automation script works completely independent from all others. Their
interaction occurs exclusively through tags that they put on datasets and
histories.

Because they are independent from each other the scripts are also configured
independent from one another. You will find one `*-job.yml.sample` file per
script inside the `job-yml-templates` folder.

To configure any of the scripts:

1. Start by copying its `job.yml.sample` file and name the copy the same as the original but without the `.sample` suffix, *e.g.* for the variation script:

   `cp variation-job.yml.sample variation-job.yml`

2. Open the newly created copy in your favorite editor and modify the lines starting with `#` in the first section and lines starting with `galaxy_id` throughout the file to customize the corresponding script's behavior.

   *Important* notes:

   Do **not** change any lines beyond the first section unless they start with
   `galaxy_id:` (see below)!

   For any line you *do* change, edit only the *value* (anything to the right
   of the `:`; in particular, do *not* uncomment lines) and make sure that you
   preserve the space between the `:` and the value!

   Do *not* enclose values in quotes!

   - Since each of the scripts is going to execute a specific Galaxy workflow as part of its action, you will need to configure at a minimum:

     - the Galaxy server the workflow should be run on
     - the ID of the workflow on the server

     The default values for `use_server` and `use_workflow_id` in the
     `job.yml.sample` files would trigger execution of publicly accessible
     SARS-CoV-2 workflows on usegalaxy.eu, but if you would like to target
     another Galaxy instance, you need to make sure corresponding workflows are
     available to your user account there, get their workflow IDs and add them
     to the `job.yml` files.

   - Each automation script will produce output in its own dedicated history.

     Two other parameters you may, thus, want to customize are:

     - the base name of the histories produced by each script and
     - the tag that the script will put on these histories to label them as the
       result of an automation script run

     The defaults are the base names and tags chosen for the COG-UK tracking
     efforts of covid19.galaxyproject.org. Change them to whatever makes sense
     for your purpose.

   - The `variation-job.yml` file contains four additional configuration options, which determine how the variation script locates the raw data to download, and where it is going to download the data to:

     - `history_for_downloads`

       should be set to the ID of a (preferably empty) history you own on the
       target Galaxy server.
       All runs of the variation script will use this history as a
       common staging area and upload batches of raw data into it.
       You may want to purge the data in this history occasionally if it has
       been processed by subsequent runs of the variation workflow.

     The variation script will download the raw data to analyze from links
     listed in datasets found in collections in dedicated *metadata* histories.

     - `metadata_history_tag`

       This specifies the history tag that identifies any of the histories
       under your user account as a *metadata* history to scan for dataset
       collections with download links

     - `metadata_collection_name`

       This specifies the name that identifies a collection in any *metadata*
       history as one holding download link datasets.

     - `download_protocol`

       The transport protocol to assume if links do not specify it.
       If links specify the protocol, this will take precedence over the config
       value.

       Examples: `ftp`, `http`

   - With the exception of the export script, each script requires some reference datasets to function properly.

     These datasets will be identical for all runs of the script and are
     expected to be accessible from your user account on the target Galaxy
     instance. You need to specify the IDs of these reference datasets on the
     target Galaxy instance on lines starting with `galaxy_id:`.

     The default values correspond to publicly accessible reference datasets
     on usegalaxy.eu, but you will need to adjust them if you want to have a
     script target a different server.

     *Important*: Do **not** change `galaxy_id` values enclosed in curly braces
     (`{}`) since these values are placeholders that will be filled by their
     script at runtime!

### Running it

#### Manually run a script

1. If the virtual environment is not active, activate it now with:

   `. planemo_sars-cov2/bin/activate`

2. Make your API Key accessible to the script, e.g., via:

   `export API_KEY=<your API key>`

   where <your API key> needs to be replaced with the actual API key associated
   with your user account on the target Galaxy instance.

   *Note*: Your API key replaces your standard login credentials (user name
   and password). As such it should be kept as securely as your password and
   you may not want to type it into your terminal as suggested in the simple
   example above.
   Consider storing the key in a file that only you have read access to and
   read it into the `API_KEY` variable from there instead.

3. Run the desired script with, e.g.:

   ./run_variation.sh

   Each of the scripts will scan your histories for tags indicating that there
   is new data waiting to be processed. If there isn't the script run will
   terminate immediately.

   The computationally heaviest variation script will check in addition that

   - no prior invocation of itself is currently at the downloading data stage
   - its last invocation has all parallel execution steps scheduled and has 2/3
     of its jobs completed

   These precautions reduce the risk of overloading the target Galaxy server by
   running the scripts too frequently.

#### Automating script runs

Since all scripts communicate exclusively via standard Galaxy tags automating
their execution is not tied to any particular scheduling system. You could use,
*e,g,* cron jobs or systemd timers for scheduling.

The only prerequisite is that, as in the manual steps above, the scheduler

- activates the virtual environment and
- sets the `API_KEY` variable

before executing any of the automation scripts.

*Note*: On usegalaxy.eu we are using our Jenkins server to schedule runs of the scripts for our COG-UK tracking efforts. If you are interested in having us schedule your own analysis runs for you, just ask us.

