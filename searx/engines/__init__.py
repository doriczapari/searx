
'''
searx is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

searx is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with searx. If not, see < http://www.gnu.org/licenses/ >.

(C) 2013- by Adam Tauber, <asciimoo@gmail.com>
'''

from os.path import realpath, dirname, splitext, join
import sys
from imp import load_source
from flask.ext.babel import gettext
from operator import itemgetter
from searx import settings

engine_dir = dirname(realpath(__file__))

engines = {}

categories = {'general': []}

engine_shortcuts = {}


def load_module(filename):
    modname = splitext(filename)[0]
    if modname in sys.modules:
        del sys.modules[modname]
    filepath = join(engine_dir, filename)
    module = load_source(modname, filepath)
    module.name = modname
    return module


def load_engine(engine_data):
    engine_name = engine_data['engine']
    engine = load_module(engine_name + '.py')

    for param_name in engine_data:
        if param_name == 'engine':
            continue
        if param_name == 'categories':
            if engine_data['categories'] == 'none':
                engine.categories = []
            else:
                engine.categories = map(
                    str.strip, engine_data['categories'].split(','))
            continue
        setattr(engine, param_name, engine_data[param_name])

    if not hasattr(engine, 'paging'):
        engine.paging = False

    if not hasattr(engine, 'categories'):
        engine.categories = ['general']

    if not hasattr(engine, 'language_support'):
        # engine.language_support = False
        engine.language_support = True

    if not hasattr(engine, 'timeout'):
        # engine.language_support = False
        engine.timeout = settings['server']['request_timeout']

    if not hasattr(engine, 'shortcut'):
        # engine.shortcut = '''
        engine.shortcut = ''

    # checking required variables
    for engine_attr in dir(engine):
        if engine_attr.startswith('_'):
            continue
        if getattr(engine, engine_attr) is None:
            print '[E] Engine config error: Missing attribute "{0}.{1}"'.format(engine.name, engine_attr)  # noqa
            sys.exit(1)

    engine.stats = {
        'result_count': 0,
        'search_count': 0,
        'page_load_time': 0,
        'score_count': 0,
        'errors': 0
    }

    if hasattr(engine, 'categories'):
        for category_name in engine.categories:
            categories.setdefault(category_name, []).append(engine)
    else:
        categories['general'].append(engine)

    if engine.shortcut:
        # TODO check duplications
        engine_shortcuts[engine.shortcut] = engine.name
    return engine


def get_engines_stats():
    # TODO refactor
    pageloads = []
    results = []
    scores = []
    errors = []
    scores_per_result = []

    max_pageload = max_results = max_score = max_errors = max_score_per_result = 0  # noqa
    for engine in engines.values():
        if engine.stats['search_count'] == 0:
            continue
        results_num = \
            engine.stats['result_count'] / float(engine.stats['search_count'])
        load_times = engine.stats['page_load_time'] / float(engine.stats['search_count'])  # noqa
        if results_num:
            score = engine.stats['score_count'] / float(engine.stats['search_count'])  # noqa
            score_per_result = score / results_num
        else:
            score = score_per_result = 0.0
        max_results = max(results_num, max_results)
        max_pageload = max(load_times, max_pageload)
        max_score = max(score, max_score)
        max_score_per_result = max(score_per_result, max_score_per_result)
        max_errors = max(max_errors, engine.stats['errors'])
        pageloads.append({'avg': load_times, 'name': engine.name})
        results.append({'avg': results_num, 'name': engine.name})
        scores.append({'avg': score, 'name': engine.name})
        errors.append({'avg': engine.stats['errors'], 'name': engine.name})
        scores_per_result.append({
            'avg': score_per_result,
            'name': engine.name
        })

    for engine in pageloads:
        if max_pageload:
            engine['percentage'] = int(engine['avg'] / max_pageload * 100)
        else:
            engine['percentage'] = 0

    for engine in results:
        if max_results:
            engine['percentage'] = int(engine['avg'] / max_results * 100)
        else:
            engine['percentage'] = 0

    for engine in scores:
        if max_score:
            engine['percentage'] = int(engine['avg'] / max_score * 100)
        else:
            engine['percentage'] = 0

    for engine in scores_per_result:
        if max_score_per_result:
            engine['percentage'] = int(engine['avg']
                                       / max_score_per_result * 100)
        else:
            engine['percentage'] = 0

    for engine in errors:
        if max_errors:
            engine['percentage'] = int(float(engine['avg']) / max_errors * 100)
        else:
            engine['percentage'] = 0

    return [
        (
            gettext('Page loads (sec)'),
            sorted(pageloads, key=itemgetter('avg'))
        ),
        (
            gettext('Number of results'),
            sorted(results, key=itemgetter('avg'), reverse=True)
        ),
        (
            gettext('Scores'),
            sorted(scores, key=itemgetter('avg'), reverse=True)
        ),
        (
            gettext('Scores per result'),
            sorted(scores_per_result, key=itemgetter('avg'), reverse=True)
        ),
        (
            gettext('Errors'),
            sorted(errors, key=itemgetter('avg'), reverse=True)
        ),
    ]


if 'engines' not in settings or not settings['engines']:
    print '[E] Error no engines found. Edit your settings.yml'
    exit(2)

for engine_data in settings['engines']:
    engine = load_engine(engine_data)
    engines[engine.name] = engine
