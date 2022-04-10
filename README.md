DCASE Benchmarks
================

*Have you ever searched for the state-of-the-art performance on a dataset, and if so, how were you sure you found it?*

DCASE Benchmarks is a centralized, community-driven repository to keep track of state-of-the-art performance of DCASE and related topics. The repository powers a website that serves to visualize results and access the corresponding materials. DCASE Benchmarks relies on the community, thus it uses GitHub functionality so that anyone can contribute to it. The page democratizes information and resources to anyone, including external and new members of the community.

The repository is currently in a **beta testing stage**.

Instructions to add a new publication with results
--------------------------------------------

1. Fork this repository.
2. Create a new yaml file under `publications/`, name the file using bib-style index (e.g, `publications/elizalde2022.yaml`). Use template `templates/publication_template.yaml` and update the required fields with the information from your publication. 
   1. Information about the datasets, metrics or tasks are defined in `info/datasets.yaml`, `info/metrics.yaml` and `info/tasks.yaml`
   2. If you are inserting publication using a new dataset, metric or task, add information about those into these files.
4. You can test the site and verify that the publication information will be shown properly by running `update.py` and starting the local server with `start_local_server.py`. Site can be access at http://localhost:8000/ 
5. Create a pull request (PR) to add your edits to the main repository.  

Instructions to preview the site
--------------------------------

1. Run `update.py` 
2. Start the local server with `start_local_server.py`
3. Open URL http://localhost:8000/ 

