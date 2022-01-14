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
from IPython import embed


def main(argv):
    env = Environment()
    env.loader = FileSystemLoader('templates')

    # Load indexing tables
    with open(os.path.join('info', 'applications.yaml'), 'r') as file:
        application_info = yaml.load(file, Loader=yaml.FullLoader)
    application_info = application_info['applications']
    for application_id, application in enumerate(application_info):
        application['id'] = application_id

    with open(os.path.join('info', 'datasets.yaml'), 'r') as file:
        dataset_info = yaml.load(file, Loader=yaml.FullLoader)
    dataset_info = dataset_info['datasets']
    for dataset_id, dataset in enumerate(dataset_info):
        dataset['id'] = dataset_id

    with open(os.path.join('info', 'metrics.yaml'), 'r') as file:
        metric_info = yaml.load(file, Loader=yaml.FullLoader)

    metric_info = metric_info['metrics']
    for metric_id, metric in enumerate(metric_info):
        metric['id'] = metric_id

    #with open(os.path.join('templates', 'paper_template.yaml'), 'r') as file:
    #    paper_data_template = yaml.load(file, Loader=yaml.FullLoader)

    print('Load papers')
    print('===================')
    all_results = []
    datasets = []
    applications = []

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

                md5 = hashlib.md5()
                md5.update(str(json.dumps(paper_identifier_data, sort_keys=True)).encode('utf-8'))
                item['paper']['id'] = md5.hexdigest()
                item['paper']['internal_link'] = os.path.join('papers', item['paper']['id'] + '.html')

                for result in item['results']:
                    dataset_found_from_index = False
                    for dataset in dataset_info:
                        if dataset['name'].lower() == result['dataset']['name'].lower():
                            result['dataset_id'] = dataset['id']
                            result['dataset_info'] = dataset
                            dataset_found_from_index = True
                            break

                    if not dataset_found_from_index:
                        print('[NEW DATASET FOUND]', result['dataset']['name'])

                    application_found_from_index = False
                    for application in application_info:
                        if application['tag'].lower() == result['application'].lower() or \
                                application['title'].lower() == result['application'].lower():
                            result['application_id'] = application['id']
                            result['application_info'] = application
                            application_found_from_index = True
                            break

                    if not application_found_from_index:
                        print('[NEW APPLICATION FOUND]', result['application'])

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
                            'name': result['dataset']['name'],
                            'set': result['dataset']['crossvalidation_set_name'],
                        },
                        'application': result['application']
                    }

                    md5 = hashlib.md5()
                    md5.update(str(json.dumps(result_identifier_data, sort_keys=True)).encode('utf-8'))
                    result_id = md5.hexdigest()

                    result_data = result
                    result_data['result_id'] = result_id
                    result_data['paper_id'] = item['paper']['id']
                    result_data['paper'] = item['paper']

                    all_results.append(result_data)

                    if result['dataset']['name'] not in datasets:
                        datasets.append(result['dataset']['name'])

                    if result['application'] not in applications:
                        applications.append(result['application'])

                paper_html_filename = os.path.join('docs', item['paper']['internal_link'])

                with open(paper_html_filename, "w") as fh:
                    paper_rendered = paper_template.render(
                        paper=item,
                    )
                    fh.write(paper_rendered)

    print(' ')
    print('  [DONE]')
    print(' ')

    list_template = env.get_template('item_list.html')

    print('Datasets')
    print('===================')

    if not os.path.exists(os.path.join('docs', 'datasets')):
        os.makedirs(os.path.join('docs', 'datasets'))

    for dataset in dataset_info:
        print(' [DATASET]', dataset['name'])

        paper_ids = []
        dataset_applications = {}
        for application in application_info:
            print('   [APPLICATION]', application['tag'])

            dataset_application_wise_results = []
            used_metrics = []
            result_count = 0
            for result in all_results:
                if dataset['id'] == result['dataset_id'] and application['id'] == result['application_id']:
                    dataset_application_wise_results.append(result)
                    result_count += 1
                    if result['paper_id'] not in paper_ids:
                        paper_ids.append(result['paper_id'])

                    if result['application_id'] not in dataset_applications:
                        dataset_applications[result['application_id']] = application

                    for value in result['performance']:
                        if value['metric_id'] not in used_metrics:
                            used_metrics.append(value['metric_id'])

            if dataset_application_wise_results:
                # Results found for dataset + application
                used_metrics_dict = {}
                for metric_id in used_metrics:
                    used_metrics_dict[metric_info[metric_id]['name']] = metric_info[metric_id]

                html_filename = os.path.join('docs', 'datasets', dataset['tag'] + '-' + application['tag'] + '.html')

                # to save the results
                with open(html_filename, "w") as fh:
                    item_rendered = list_template.render(
                        dataset=dataset,
                        application=application,
                        results=dataset_application_wise_results,
                        used_metrics=used_metrics_dict,
                        primary_metric=dataset['primary_metric'][application['tag']]
                    )
                    fh.write(item_rendered)

        dataset['paper_count'] = len(paper_ids)
        dataset['result_count'] = result_count
        #dataset['list_filename'] = os.path.join('datasets', dataset['tag']+'.html')
        dataset['applications'] = list(dataset_applications.values())

    print(' ')

    print('Applications')
    print('===================')
    for application in sorted(applications):
        print(' ', application)
    print(' ')

    # Index page
    index_template = env.get_template('index.html')
    index_html_filename = os.path.join('docs', 'index.html')
    with open(index_html_filename, "w") as fh:
        index_rendered = index_template.render(
            applications=application_info,
            datasets=dataset_info
        )
        fh.write(index_rendered)

    #embed()

    print(' ')
    print('  [DONE]')


if __name__ == "__main__":
    sys.exit(main(sys.argv))