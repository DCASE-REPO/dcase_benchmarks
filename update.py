#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import glob
import yaml
import json
import hashlib
import requests
from jinja2 import Template
from jinja2 import FileSystemLoader
from jinja2.environment import Environment
from slugify import slugify
#from IPython import embed


def main(argv):
    env = Environment()
    env.loader = FileSystemLoader('templates')
    print('DCASE Benchmarks / Site generation')
    print(' ')

    # Handle tasks
    # ===========================================================
    print('Load tasks')
    print('===================')
    with open(os.path.join('info', 'tasks.yaml'), 'r') as file:
        task_info = yaml.load(file, Loader=yaml.FullLoader)
    task_info = task_info['tasks']
    for task_id, task in enumerate(task_info):
        task['id'] = task_id
    print(' ')
    print('  [DONE]')
    print(' ')

    # Handle datasets
    # ===========================================================
    print('Load datasets')
    print('===================')
    with open(os.path.join('info', 'datasets.yaml'), 'r') as file:
        dataset_info = yaml.load(file, Loader=yaml.FullLoader)
    dataset_info = dataset_info['datasets']

    url = 'https://raw.githubusercontent.com/DCASE-REPO/dcase_datalist/main/docs/datasets.json'
    resp = requests.get(url)
    data = json.loads(resp.text)
    datalist_information = {}
    for item in data:
        datalist_information[item['dataset-id']] = item

    for dataset_id, dataset in enumerate(dataset_info):
        dataset['id'] = dataset_id
        d_tasks = {}
        for item in dataset['tasks']:
            m = {}
            for metric_item in item['metrics']:
                m[metric_item['metric']] = metric_item
            item['metrics'] = m
            item['used'] = False
            item['result_count'] = 0
            d_tasks[item['tag']] = item

        dataset['task_dict'] = d_tasks

        if dataset['datalist_id'] in datalist_information:
            dataset['datalist_information'] = datalist_information[dataset['datalist_id']]
        else:
            print('  [INFO] Dataset was not found from DCASE Datalist [{name}] with datalist_id=[{dataset}]. Dataset linking between DCASE Datalist is not used for this dataset. Please check if dataset is listed in https://dcase-repo.github.io/dcase_datalist/. If not, please consider contributing the dataset information to DCASE datalist. '.format(
                name=dataset['name'],
                dataset=dataset['datalist_id']
            ))
    print(' ')
    print('  [DONE]')
    print(' ')

    # Handle metrics
    # ===========================================================
    print('Load metrics')
    print('===================')
    with open(os.path.join('info', 'metrics.yaml'), 'r') as file:
        metric_info = yaml.load(file, Loader=yaml.FullLoader)

    metric_info = metric_info['metrics']
    for metric_id, metric in enumerate(metric_info):
        metric['id'] = metric_id

    list_template = env.get_template('item_list.html')
    print(' ')
    print('  [DONE]')
    print(' ')

    # Handle publication entries
    # ===========================================================
    print('Load publications')
    print('===================')
    all_results = []
    datasets = []
    tasks = []
    all_publications = {}
    all_datasets = {}
    all_tasks = {}

    publication_template = env.get_template('publication.html')
    if not os.path.exists(os.path.join('docs', 'publications')):
        os.makedirs(os.path.join('docs', 'publications'))

    publications = glob.glob(os.path.join('publications') + "/*.yaml")
    for publication_filename in publications:
        with open(publication_filename, 'r') as file:
            item = yaml.load(file, Loader=yaml.FullLoader)

            if not item.get('skip', False):
                print(' ', publication_filename)
                publication_identifier_data = {
                    'authors': item['publication']['authors'],
                    'title': item['publication']['title'],
                    'year': item['publication']['year']
                }
                item['publication']['label'] = item['publication']['authors'][0]['lastname']+str(item['publication']['year'])
                item['publication']['sort_label'] = str(item['publication']['year']) + item['publication']['authors'][0]['lastname']

                authors = []
                for author in item['publication']['authors']:
                    authors.append(author['firstname']+' '+author['lastname'])
                item['publication']['authors_string'] = ', '.join(authors)

                md5 = hashlib.md5()
                md5.update(str(json.dumps(publication_identifier_data, sort_keys=True)).encode('utf-8'))
                item['publication']['id'] = md5.hexdigest()
                item['publication']['slug'] = slugify(item['publication']['authors'][0]['lastname']+'-'+str(item['publication']['year'])+'-'+str(item['publication']['title']))
                item['publication']['internal_link'] = os.path.join('publications', item['publication']['slug'] + '.html')
                item['publication']['datasets'] = {}
                item['publication']['tasks'] = {}

                for result in item['results']:
                    dataset_found_from_index = False
                    for dataset in dataset_info:
                        if dataset['tag'].lower() == result['dataset']['tag'].lower():
                            result['dataset_id'] = dataset['id']
                            result['dataset_info'] = dataset
                            dataset_found_from_index = True
                            break
                    item['publication']['datasets'][result['dataset_id']] = result['dataset_info']

                    all_datasets[result['dataset_info']['tag']] = result['dataset_info']

                    if not dataset_found_from_index:
                        print('[NEW DATASET FOUND]', result['dataset_info']['name'])

                    task_found_from_index = False
                    for task in task_info:
                        if task['tag'].lower() == result['task'].get('tag', '').lower() or \
                                task['title'].lower() == result['task'].get('title', '').lower():
                            result['task_id'] = task['id']
                            result['task_tag'] = task['tag']
                            result['task_info'] = task
                            task_found_from_index = True
                            break

                    all_tasks[result['task_tag']] = result['task_info']
                    result['internal_link'] = os.path.join('..', 'datasets', result['dataset_info']['tag'] + '-' + result['task_info']['tag'] + '.html')

                    if 'dataset_dict' not in all_tasks[result['task_tag']]:
                        all_tasks[result['task_tag']]['dataset_dict'] = {}
                    if result['dataset_id'] not in all_tasks[result['task_tag']]['dataset_dict']:
                        all_tasks[result['task_tag']]['dataset_dict'][result['dataset_id']] = result['dataset_info']
                        all_tasks[result['task_tag']]['dataset_dict'][result['dataset_id']]['result_count'] = 0

                    all_tasks[result['task_tag']]['dataset_dict'][result['dataset_id']]['used'] = True
                    all_tasks[result['task_tag']]['dataset_dict'][result['dataset_id']]['result_count'] += 1

                    item['publication']['tasks'][result['task_id']] = result['task_info']

                    all_datasets[result['dataset_info']['tag']]['task_dict'][result['task_tag']]['used'] = True
                    all_datasets[result['dataset_info']['tag']]['task_dict'][result['task_tag']]['result_count'] += 1

                    if not task_found_from_index:
                        print('[NEW TASK FOUND]', result['task'])

                    for performance in result['performance']:
                        metric_found_from_index = False
                        for metric in metric_info:
                            if metric['name'].lower() == performance['metric'].lower():
                                performance['metric_id'] = metric['id']
                                metric_found_from_index = True
                                break

                        if not metric_found_from_index:
                            print('[NEW METRIC FOUND]', performance['metric'])

                    result_identifier_data = {
                        'publication_id': item['publication']['id'],
                        'identifier': result['identifier'],
                        'dataset': {
                            'tag': result['dataset_info']['tag'],
                            'name': result['dataset_info']['name'],
                        },
                        'task': result['task'],
                    }

                    md5 = hashlib.md5()
                    md5.update(str(json.dumps(result_identifier_data, sort_keys=True)).encode('utf-8'))
                    result_id = md5.hexdigest()

                    result_data = result
                    result_data['result_id'] = result_id
                    result_data['publication_id'] = item['publication']['id']
                    result_data['publication'] = item['publication']

                    all_results.append(result_data)

                    if result['dataset']['tag'] not in datasets:
                        datasets.append(result['dataset']['tag'])

                    if result['task'] not in tasks:
                        tasks.append(result['task'])

                all_publications[item['publication']['sort_label']+item['publication']['id']] = item['publication']

                publication_html_filename = os.path.join('docs', item['publication']['internal_link'])

                with open(publication_html_filename, "w") as fh:
                    publication_rendered = publication_template.render(
                        publication=item,
                    )
                    fh.write(publication_rendered)

    print(' ')
    print('  [DONE]')
    print(' ')

    # Handle publication index
    # ===========================================================
    print('Create publication index')
    print('===================')
    publications_template = env.get_template('publications.html')
    publications_html_filename = os.path.join('docs', 'publications.html')
    with open(publications_html_filename, "w") as fh:
        index_rendered = publications_template.render(
            publications=all_publications
        )
        fh.write(index_rendered)
    print('  Number of publications:', len(all_publications))
    print(' ')
    print('  [DONE]')
    print(' ')

    # Handle dataset wise pages
    # ===========================================================
    print('Datasets')
    print('===================')
    if not os.path.exists(os.path.join('docs', 'datasets')):
        os.makedirs(os.path.join('docs', 'datasets'))

    for dataset in dataset_info:
        print(' [DATASET]', dataset['name'])

        publication_ids = []
        dataset_tasks = {}
        result_count = 0
        for task in task_info:
            print('   [TASK]', task['tag'])

            dataset_task_wise_results = []
            used_metrics = []
            for result in all_results:
                if dataset['id'] == result['dataset_id'] and task['id'] == result['task_id']:
                    dataset_task_wise_results.append(result)
                    result_count += 1
                    if result['publication_id'] not in publication_ids:
                        publication_ids.append(result['publication_id'])

                    if result['task_id'] not in dataset_tasks:
                        dataset_tasks[result['task_id']] = task

                    for value in result['performance']:
                        if value['metric_id'] not in used_metrics:
                            used_metrics.append(value['metric_id'])

            if dataset_task_wise_results:
                # Results found for dataset + task
                used_metrics_dict = {}
                for metric_id in used_metrics:
                    used_metrics_dict[metric_info[metric_id]['name']] = metric_info[metric_id]

                html_filename = os.path.join('docs', 'datasets', dataset['tag'] + '-' + task['tag'] + '.html')

                default_sorting_metric = dataset['task_dict'][task['tag']]['default_metric_for_table_sorting']

                # to save the results
                with open(html_filename, "w") as fh:
                    item_rendered = list_template.render(
                        dataset=dataset,
                        task=task,
                        results=dataset_task_wise_results,
                        used_metrics=used_metrics_dict,
                        default_sorting_metric=dataset['task_dict'][task['tag']]['metrics'][default_sorting_metric]
                    )
                    fh.write(item_rendered)

        dataset['publication_count'] = len(publication_ids)
        dataset['result_count'] = result_count

        #dataset['list_filename'] = os.path.join('datasets', dataset['tag']+'.html')
        dataset['task_list'] = list(dataset_tasks.values())
    print(' ')

    # Handle dataset index
    # ===========================================================
    print('Create dataset index')
    print('===================')
    datasets_template = env.get_template('datasets.html')
    datasets_html_filename = os.path.join('docs', 'datasets.html')
    with open(datasets_html_filename, "w") as fh:
        index_rendered = datasets_template.render(
            datasets=all_datasets
        )
        fh.write(index_rendered)
    print('  Number of datasets:', len(all_publications))
    print(' ')
    print('  [DONE]')
    print(' ')

    # Handle task wise pages
    # ===========================================================
    print('Tasks')
    print('===================')
    for task in sorted(tasks, key=lambda x: x['tag']):
        print(' ', task['tag'])
    print(' ')

    # Handle task index
    # ===========================================================
    print('Create task index')
    print('===================')
    tasks_template = env.get_template('tasks.html')
    tasks_html_filename = os.path.join('docs', 'tasks.html')
    with open(tasks_html_filename, "w") as fh:
        index_rendered = tasks_template.render(
            tasks=all_tasks
        )
        fh.write(index_rendered)
    print('  Number of tasks:', len(all_publications))
    print(' ')
    print('  [DONE]')
    print(' ')

    # Index page
    index_template = env.get_template('index.html')
    index_html_filename = os.path.join('docs', 'index.html')
    with open(index_html_filename, "w") as fh:
        index_rendered = index_template.render(
            tasks=task_info,
            datasets=dataset_info
        )
        fh.write(index_rendered)
    print(' ')

    # About page
    about_template = env.get_template('about.html')
    about_html_filename = os.path.join('docs', 'about.html')
    with open(about_html_filename, "w") as fh:
        about_rendered = about_template.render(
            tasks=task_info,
            datasets=dataset_info
        )
        fh.write(about_rendered)
    print(' ')

    #

if __name__ == "__main__":
    sys.exit(main(sys.argv))