#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import glob
import yaml
import json
import hashlib
from jinja2 import Template
from jinja2 import FileSystemLoader
from jinja2.environment import Environment
from slugify import slugify

from IPython import embed


def main(argv):
    env = Environment()
    env.loader = FileSystemLoader('templates')

    # Load indexing tables
    # ===========================================================
    with open(os.path.join('info', 'tasks.yaml'), 'r') as file:
        task_info = yaml.load(file, Loader=yaml.FullLoader)
    task_info = task_info['tasks']
    for task_id, task in enumerate(task_info):
        task['id'] = task_id

    with open(os.path.join('info', 'datasets.yaml'), 'r') as file:
        dataset_info = yaml.load(file, Loader=yaml.FullLoader)
    dataset_info = dataset_info['datasets']

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

    with open(os.path.join('info', 'metrics.yaml'), 'r') as file:
        metric_info = yaml.load(file, Loader=yaml.FullLoader)

    metric_info = metric_info['metrics']
    for metric_id, metric in enumerate(metric_info):
        metric['id'] = metric_id

    list_template = env.get_template('item_list.html')

    # Handle paper entries
    # ===========================================================
    print('Load papers')
    print('===================')
    all_results = []
    datasets = []
    tasks = []
    all_papers = {}
    all_datasets = {}
    all_tasks = {}

    paper_template = env.get_template('paper.html')
    if not os.path.exists(os.path.join('docs', 'papers')):
        os.makedirs(os.path.join('docs', 'papers'))

    papers = glob.glob(os.path.join('papers') + "/*.yaml")
    for paper_filename in papers:
        with open(paper_filename, 'r') as file:
            item = yaml.load(file, Loader=yaml.FullLoader)
            if 'skip' not in item or item['skip'] is False:
                print(' ', paper_filename)
                paper_identifier_data = {
                    'authors': item['paper']['authors'],
                    'title': item['paper']['title'],
                    'year': item['paper']['year']
                }
                item['paper']['label'] = item['paper']['authors'][0]['lastname']+str(item['paper']['year'])
                item['paper']['sort_label'] = str(item['paper']['year']) + item['paper']['authors'][0]['lastname']

                md5 = hashlib.md5()
                md5.update(str(json.dumps(paper_identifier_data, sort_keys=True)).encode('utf-8'))
                item['paper']['id'] = md5.hexdigest()
                item['paper']['slug'] = slugify(item['paper']['authors'][0]['lastname']+'-'+str(item['paper']['year'])+'-'+str(item['paper']['title']))
                item['paper']['internal_link'] = os.path.join('papers', item['paper']['slug'] + '.html')
                item['paper']['datasets'] = {}
                item['paper']['tasks'] = {}
                for result in item['results']:
                    dataset_found_from_index = False
                    for dataset in dataset_info:
                        if dataset['tag'].lower() == result['dataset']['tag'].lower():
                            result['dataset_id'] = dataset['id']
                            result['dataset_info'] = dataset
                            dataset_found_from_index = True
                            break
                    item['paper']['datasets'][result['dataset_id']] = result['dataset_info']

                    all_datasets[result['dataset_info']['tag']] = result['dataset_info']

                    if not dataset_found_from_index:
                        print('[NEW DATASET FOUND]', result['dataset_info']['name'])

                    task_found_from_index = False
                    for task in task_info:
                        if task['tag'].lower() == result['task'].lower() or \
                                task['title'].lower() == result['task'].lower():
                            result['task_id'] = task['id']
                            result['task_tag'] = task['tag']
                            result['task_info'] = task
                            task_found_from_index = True
                            break

                    item['paper']['tasks'][result['task_id']] = result['task_info']

                    all_datasets[result['dataset_info']['tag']]['task_dict'][result['task_tag']]['used'] = True
                    all_datasets[result['dataset_info']['tag']]['task_dict'][result['task_tag']]['result_count'] += 1

                    if not task_found_from_index:
                        print('[NEW TASK FOUND]', result['task'])

                    for performance in result['performance']:
                        metric_found_from_index = False
                        for metric in metric_info:
                            if metric['name'].lower() == performance['metric']:
                                performance['metric_id'] = metric['id']
                                metric_found_from_index = True
                                break

                        if not metric_found_from_index:
                            print('[NEW METRIC FOUND]', performance['metric'])

                    result_identifier_data = {
                        'paper_id': item['paper']['id'],
                        'identifier': result['identifier'],
                        'dataset': {
                            'tag': result['dataset_info']['tag'],
                            'name': result['dataset_info']['name'],
                            'set': result['dataset']['performance_evaluation_set_name'],
                        },
                        'task': result['task']
                    }

                    md5 = hashlib.md5()
                    md5.update(str(json.dumps(result_identifier_data, sort_keys=True)).encode('utf-8'))
                    result_id = md5.hexdigest()

                    result_data = result
                    result_data['result_id'] = result_id
                    result_data['paper_id'] = item['paper']['id']
                    result_data['paper'] = item['paper']

                    all_results.append(result_data)

                    if result['dataset']['tag'] not in datasets:
                        datasets.append(result['dataset']['tag'])

                    if result['task'] not in tasks:
                        tasks.append(result['task'])

                all_papers[item['paper']['sort_label']+item['paper']['id']] = item['paper']

                paper_html_filename = os.path.join('docs', item['paper']['internal_link'])

                with open(paper_html_filename, "w") as fh:
                    paper_rendered = paper_template.render(
                        paper=item,
                    )
                    fh.write(paper_rendered)

    print(' ')
    print('  [DONE]')
    print(' ')

    # Handle paper index
    # ===========================================================
    print('Create paper index')
    print('===================')
    papers_template = env.get_template('papers.html')
    papers_html_filename = os.path.join('docs', 'papers.html')
    with open(papers_html_filename, "w") as fh:
        index_rendered = papers_template.render(
            papers=all_papers
        )
        fh.write(index_rendered)
    print(len(all_papers))
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

        paper_ids = []
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
                    if result['paper_id'] not in paper_ids:
                        paper_ids.append(result['paper_id'])

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

        dataset['paper_count'] = len(paper_ids)
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
    print(len(all_papers))
    print(' ')
    print('  [DONE]')
    print(' ')


    # Handle task wise pages
    # ===========================================================
    print('Tasks')
    print('===================')
    for task in sorted(tasks):
        print(' ', task)
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

    #embed()

    print(' ')
    print('  [DONE]')


if __name__ == "__main__":
    sys.exit(main(sys.argv))