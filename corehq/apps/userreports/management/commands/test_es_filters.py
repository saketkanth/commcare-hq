from django.core.management.base import LabelCommand, CommandError
from corehq.apps.userreports import tasks
from corehq.apps.userreports.filters.es_factory import FilterFactoryES
from corehq.apps.userreports.models import DataSourceConfiguration
from corehq.apps.userreports.specs import FactoryContext
from corehq.elastic import ES_META, get_es_new

INDEX_MAP = {
    'CommCareCase': 'cases',
    'XFormInstance': 'forms',
    'CommCareUser': 'users',
}

class Command(LabelCommand):
    help = "Test UCR ES filters"
    args = ''
    label = ""

    es_client = get_es_new()

    def handle(self, *args, **options):
        for datasource in DataSourceConfiguration.all():
            if datasource.base_item_expression:
                self.stderr.write("{}/{}: base_item_expression not supported: {}".format(
                    datasource.domain, datasource._id, datasource.base_item_expression
                ))
                continue

            try:
                body = _get_filter_body(datasource)
            except Exception as e:
                self.stderr.write("{}/{}: error building filters: {}".format(datasource.domain, datasource._id, e))
                continue

            query = {
                "query": {
                    "filtered": {
                        "filter": body
                    }
                },
                "size": 0
            }
            index_name = INDEX_MAP[datasource.referenced_doc_type]
            try:
                results = self._run_query(index_name, query)
            except Exception as e:
                self.stderr.write("{}/{}: ES query error: {}".format(
                    datasource.domain, datasource._id, e
                ))
                continue

            self.stdout.write("{}/{}: total docs: {}".format(datasource.domain, datasource._id, results['hits']['total']))

    def _run_query(self, index_name, query):
        es_meta = ES_META[index_name]
        return self.es_client.search(es_meta.index, es_meta.type, body=query)


def _get_filter_body(datasource):
    named_filter_objects = {
        name: FilterFactoryES.from_spec(filter, FactoryContext.empty())
        for name, filter in datasource.named_filters.items()
        }
    factory_context = FactoryContext(datasource.named_expression_objects, named_filter_objects)

    extras = (
        [datasource.configured_filter]
        if datasource.configured_filter else []
    )
    built_in_filters = [
        datasource._get_domain_filter_spec()
    ]
    return FilterFactoryES.from_spec(
        {
            'type': 'and',
            'filters': built_in_filters + extras,
        },
        context=factory_context,
    )
