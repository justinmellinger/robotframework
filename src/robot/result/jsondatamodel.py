#  Copyright 2008-2011 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import time
from robot import utils

import json


class DataModel(object):

    def __init__(self, robot_data):
        self._robot_data = robot_data
        self._settings = None
        self._set_generated(time.localtime())

    def _set_generated(self, timetuple):
        genMillis = long(time.mktime(timetuple) * 1000) -\
                        self._robot_data['baseMillis']
        self._set_attr('generatedMillis', genMillis)
        self._set_attr('generatedTimestamp',
                       utils.format_time(timetuple, gmtsep=' '))

    def _set_attr(self, name, value):
        self._robot_data[name] = value

    def set_settings(self, settings):
        self._settings = settings

    def write_to(self, output, separator=''):
        output.write('window.output = {};\n')
        output.write(separator)
        for key, value in self._robot_data.items():
            self._dump_json('window.output["%s"] = ' % key, value, output)
            output.write(separator)
        self._dump_json('window.settings = ', self._settings, output)

    def _dump_json(self, name, data, output):
        output.write(name)
        json.json_dump(data, output)
        output.write(';\n')

    def remove_keywords(self):
        self._robot_data['suite'] = self._remove_keywords_from(self._robot_data['suite'])
        self._prune_unused_indices()

    def _remove_keywords_from(self, data):
        if not isinstance(data, list):
            return data
        return [self._remove_keywords_from(item) for item in data
                if not self._is_ignorable_keyword(item)]

    def _is_ignorable_keyword(self, item):
        # Top level teardown is kept to make tests fail if suite teardown failed
        # TODO: Could we store information about failed suite teardown otherwise?
        # TODO: Cleanup?
        return isinstance(item, list) and item and item[0] > 0 \
            and self._robot_data['strings'][item[0]] in ['*kw', '*setup', '*forloop', '*foritem']

    def _prune_unused_indices(self):
        used = self._collect_used_indices(self._robot_data['suite'], set())
        remap = {}
        self._robot_data['strings'] = \
            list(self._prune(self._robot_data['strings'], used, remap))
        self._robot_data['integers'] = \
            list(self._prune(self._robot_data['integers'], used, remap,
                             map_index=lambda index: -1 - index,
                             offset_increment=-1))
        self._remap_indices(self._robot_data['suite'], remap)

    def _prune(self, data, used, index_remap, map_index=None, offset_increment=1):
        offset = 0
        for index, text in enumerate(data):
            index = map_index(index) if map_index else index
            if index in used:
                index_remap[index] = index - offset
                yield text
            else:
                offset += offset_increment

    def _remap_indices(self, data, remap):
        for i, item in enumerate(data):
            if isinstance(item, (int, long)):
                data[i] = remap[item]
            elif isinstance(item, list):
                self._remap_indices(item, remap)
            elif isinstance(item, dict):
                new_dict = {}
                for k,v in item.items():
                    new_dict[remap[k]] = remap[v]
                data[i] = new_dict

    def _collect_used_indices(self, data, result):
        for item in data:
            if isinstance(item, (int, long)):
                result.add(item)
            elif isinstance(item, list):
                self._collect_used_indices(item, result)
            elif isinstance(item, dict):
                self._collect_used_indices(item.values(), result)
                self._collect_used_indices(item.keys(), result)
        return result

