
from collections import OrderedDict
import json


class Tags(object):
    def __init__(self):
        self.tree = OrderedDict()
        self.tags = set()

    def setup(self, jobs):
        self._build_tree(jobs)

    def _build_tree(self, jobs):
        """@SLURMY
        Build job tag hierarchy tree from the list of jobs.
        """
        ## Get tag counts and sets of tags
        counts = {}
        tag_set = set()
        for job in jobs:
            tags = sorted(job.tags)
            for tag in tags:
                self.tags.add(tag)
                if tag not in counts: counts[tag] = 0
                counts[tag] += 1
            tag_set.add(json.dumps(tags))
        ## Recursive function for adding tags to the tag tree
        def add(tags, tree, prev_count = None, prev_tag = None):
            if len(tags) == 0:
                return
            tag = tags.pop(0)
            if prev_count is None or counts[tag] == prev_count:
                if tag not in tree:
                    tree[tag] = OrderedDict()
                prev_tag = tag
                prev_count = counts[tag]
                add(tags, tree, prev_count, prev_tag)
            else:
                if tag not in tree[prev_tag]:
                    tree[prev_tag][tag] = OrderedDict()
                new_prev_tag = tag
                prev_count = counts[tag]
                add(tags, tree[prev_tag], prev_count, new_prev_tag)
        ## Fill tag hierarchy tree
        for tags in tag_set:
            ## Sort tags according to the count
            tags = json.loads(tags)
            tags = sorted(tags, key = lambda x: counts[x], reverse = True)
            ## Add tags to tag tree
            add(tags, self.tree)
