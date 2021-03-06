from casexml.apps.case.models import CommCareCase
from corehq.apps.hqcase.management.commands.ptop_fast_reindexer import ElasticReindexer
from corehq.pillows.case import CasePillow


class Command(ElasticReindexer):
    help = "Fast reindex of case elastic index by using the case view and reindexing cases"

    doc_class = CommCareCase
    view_name = 'cases_by_owner/view'
    pillow_class = CasePillow

    @staticmethod
    def sort_key(row):
        return row['doc'].get('server_modified_on', 'None')
