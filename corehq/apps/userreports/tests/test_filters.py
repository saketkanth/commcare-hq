from django.test import SimpleTestCase
from corehq.apps.userreports.exceptions import BadSpecError
from corehq.apps.userreports.filters import ANDFilter, ORFilter, NOTFilter
from corehq.apps.userreports.filters.es_factory import FilterFactoryES
from corehq.apps.userreports.filters.factory import FilterFactory
from corehq.apps.userreports.specs import FactoryContext


class PropertyMatchFilterTestMixin(object):
    filter_factory = None

    def get_filter(self):
        return self.filter_factory.from_spec({
            'type': 'property_match',
            'property_name': 'foo',
            'property_value': 'bar',
        })

    def get_path_filter(self):
        return self.filter_factory.from_spec({
            'type': 'property_match',
            'property_path': ['path', 'to', 'foo'],
            'property_value': 'bar',
        })



class PropertyMatchFilterTest(SimpleTestCase, PropertyMatchFilterTestMixin):
    filter_factory = FilterFactory

    def test_normal_filter(self):
        # just asserting that this doesn't raise any exceptions
        self.get_filter()

    def test_filter_with_path(self):
        # just asserting that this doesn't raise any exceptions
        self.get_path_filter()

    def test_no_name_or_path(self):
        with self.assertRaises(BadSpecError):
            FilterFactory.from_spec({
                'type': 'property_match',
                'property_value': 'bar',
            })

    def test_empty_name(self):
        with self.assertRaises(BadSpecError):
            FilterFactory.from_spec({
                'type': 'property_match',
                'property_name': '',
                'property_value': 'bar',
            })

    def test_name_no_value(self):
        with self.assertRaises(BadSpecError):
            FilterFactory.from_spec({
                'type': 'property_match',
                'property_name': 'foo',
            })

    def test_empty_path(self):
        with self.assertRaises(BadSpecError):
            FilterFactory.from_spec({
                'type': 'property_match',
                'property_path': [],
                'property_value': 'bar',
            })

    def test_filter_match(self):
        self.assertTrue(self.get_filter()(dict(foo='bar')))

    def test_filter_no_match(self):
        self.assertFalse(self.get_filter()(dict(foo='not bar')))

    def test_filter_missing(self):
        self.assertFalse(self.get_filter()(dict(not_foo='bar')))

    def test_filter_path_match(self):
        self.assertTrue(self.get_path_filter()({'path': {'to': {'foo': 'bar'}}}))

    def test_filter_path_no_match(self):
        self.assertFalse(self.get_path_filter()({'path': {'to': {'foo': 'not bar'}}}))

    def test_path_filter_missing(self):
        self.assertFalse(self.get_path_filter()({'path': {'to': {'not_foo': 'bar'}}}))
        self.assertFalse(self.get_path_filter()({'foo': 'bar'}))

    def test_null_value(self):
        null_filter = FilterFactory.from_spec({
            'type': 'property_match',
            'property_name': 'foo',
            'property_value': None,
        })
        self.assertEqual(True, null_filter({'foo': None}))
        self.assertEqual(True, null_filter({}))
        self.assertEqual(False, null_filter({'foo': 'exists'}))
        self.assertEqual(False, null_filter({'foo': ''}))


class PropertyMatchFilterTestES(SimpleTestCase, PropertyMatchFilterTestMixin):
    filter_factory = FilterFactoryES

    def test_normal_filter(self):
        es_filter = self.get_filter()
        self.assertEqual(es_filter, {
            'term': {'foo': 'bar'}
        })

    def test_filter_with_path(self):
        es_filter = self.get_path_filter()
        self.assertEqual(es_filter, {
            'term': {'path.to.foo': 'bar'}
        })

    def test_no_name_or_path(self):
        with self.assertRaises(BadSpecError):
            FilterFactoryES.from_spec({
                'type': 'property_match',
                'property_value': 'bar',
            })

    def test_empty_name(self):
        with self.assertRaises(BadSpecError):
            FilterFactoryES.from_spec({
                'type': 'property_match',
                'property_name': '',
                'property_value': 'bar',
            })

    def test_name_no_value(self):
        with self.assertRaises(BadSpecError):
            FilterFactoryES.from_spec({
                'type': 'property_match',
                'property_name': 'foo',
            })

    def test_empty_path(self):
        with self.assertRaises(BadSpecError):
            FilterFactoryES.from_spec({
                'type': 'property_match',
                'property_path': [],
                'property_value': 'bar',
            })


class EqualityFilterTestMixin(object):
    factory_class = None

    def get_filter(self):
        return self.factory_class.from_spec({
            'type': 'boolean_expression',
            'expression': {
                'type': 'property_name',
                'property_name': 'foo',
            },
            'operator': 'eq',
            'property_value': 'bar',
        })

    def get_path_filter(self):
        return self.factory_class.from_spec({
            'type': 'boolean_expression',
            'expression': {
                'type': 'property_path',
                'property_path': ['path', 'to', 'foo'],
            },
            'operator': 'eq',
            'property_value': 'bar',
        })


class EqualityFilterTest(EqualityFilterTestMixin, PropertyMatchFilterTest):
    factory_class = FilterFactory


class EqualityFilterTestES(EqualityFilterTestMixin, PropertyMatchFilterTestES):
    factory_class = FilterFactoryES


class BooleanExpressionFilterMixin(object):
    filter_factory = None

    def get_filter(self, operator, value):
        return self.filter_factory.from_spec({
            'type': 'boolean_expression',
            'expression': {
                'type': 'property_name',
                'property_name': 'foo',
            },
            'operator': operator,
            'property_value': value,
        })


class BooleanExpressionFilterTest(BooleanExpressionFilterMixin, SimpleTestCase):
    filter_factory = FilterFactory

    def test_equal(self):
        match = 'match'
        filter = self.get_filter('eq', match)
        self.assertTrue(filter({'foo': match}))
        self.assertFalse(filter({'foo': 'non-match'}))
        self.assertFalse(filter({'foo': None}))

    def test_equal_null(self):
        null_filter = self.get_filter('eq', None)
        self.assertEqual(True, null_filter({'foo': None}))
        self.assertEqual(True, null_filter({}))
        self.assertEqual(False, null_filter({'foo': 'exists'}))
        self.assertEqual(False, null_filter({'foo': ''}))

    def test_in(self):
        values = ['a', 'b', 'c']
        filter = self.get_filter('in', values)
        for value in values:
            self.assertTrue(filter({'foo': value}))
        for value in ['d', 'e', 'f']:
            self.assertFalse(filter({'foo': value}))

    def test_in_multiselect(self):
        filter = self.get_filter('in_multi', 'a')
        self.assertTrue(filter({'foo': 'a'}))
        self.assertTrue(filter({'foo': 'a b c'}))
        self.assertTrue(filter({'foo': 'b c a'}))
        self.assertFalse(filter({'foo': 'b'}))
        self.assertFalse(filter({'foo': 'abc'}))
        self.assertFalse(filter({'foo': 'ab cd'}))
        self.assertFalse(filter({'foo': 'd e f'}))

    def test_less_than(self):
        filter = self.get_filter('lt', 3)
        for match in (-10, 0, 2):
            self.assertTrue(filter({'foo': match}))
        for non_match in (3, 11, '2'):
            self.assertFalse(filter({'foo': non_match}))

    def test_less_than_equal(self):
        filter = self.get_filter('lte', 3)
        for match in (-10, 0, 2, 3):
            self.assertTrue(filter({'foo': match}))
        for non_match in (4, 11, '2'):
            self.assertFalse(filter({'foo': non_match}))

    def test_greater_than(self):
        filter = self.get_filter('gt', 3)
        for match in (4, 11, '2'):
            self.assertTrue(filter({'foo': match}))
        for non_match in (-10, 0, 2, 3):
            self.assertFalse(filter({'foo': non_match}))

    def test_greater_than_equal(self):
        filter = self.get_filter('gte', 3)
        for match in (3, 11, '2'):
            self.assertTrue(filter({'foo': match}))
        for non_match in (-10, 0, 2):
            self.assertFalse(filter({'foo': non_match}))

    def test_date_conversion(self):
        filter_with_date = FilterFactory.from_spec({
            "type": "boolean_expression",
            "expression": {
                "datatype": "date",
                "property_name": "visit_date",
                "type": "property_name"
            },
            "operator": "gt",
            "property_value": "2015-05-05"
        })
        self.assertFalse(filter_with_date({'visit_date': '2015-05-04'}))
        self.assertTrue(filter_with_date({'visit_date': '2015-05-06'}))

    def test_literal_in_expression(self):
        filter_with_literal = FilterFactory.from_spec({
            'type': 'boolean_expression',
            'expression': 1,
            'operator': 'gt',
            'property_value': 2
        })
        self.assertFalse(filter_with_literal({}))
        filter_with_literal = FilterFactory.from_spec({
            'type': 'boolean_expression',
            'expression': 2,
            'operator': 'gt',
            'property_value': 1
        })
        self.assertTrue(filter_with_literal({}))

    def test_expression_in_value(self):
        filter_with_exp = FilterFactory.from_spec({
            'type': 'boolean_expression',
            'expression': {
                'type': 'property_name',
                'property_name': 'foo',
            },
            'operator': 'gt',
            'property_value': {
                'type': 'property_name',
                'property_name': 'bar',
            },
        })
        self.assertTrue(filter_with_exp({'foo': 4, 'bar': 2}))
        self.assertFalse(filter_with_exp({'foo': 2, 'bar': 4}))


class BooleanExpressionFilterTestES(BooleanExpressionFilterMixin, SimpleTestCase):
    filter_factory = FilterFactoryES

    def test_equal(self):
        match = 'match'
        filter = self.get_filter('eq', match)
        self.assertEqual(filter, {
            'term': {'foo': 'match'}
        })

    def test_equal_null(self):
        null_filter = self.get_filter('eq', None)
        self.assertEqual(null_filter, {
            'missing': {'field': 'foo'}
        })

    def test_in(self):
        values = ['a', 'b', 'c']
        filter = self.get_filter('in', values)
        self.assertEqual(filter, {
            'terms': {'foo': values}
        })

    def test_in_multiselect(self):
        with self.assertRaises(BadSpecError):
            self.get_filter('in_multi', 'a')

    def test_less_than(self):
        filter = self.get_filter('lt', 3)
        self.assertEqual(filter, {
            'range': {
                'foo': {
                    'lt': 3
                }
            }
        })

    def test_less_than_equal(self):
        filter = self.get_filter('lte', 3)
        self.assertEqual(filter, {
            'range': {
                'foo': {
                    'lte': 3
                }
            }
        })

    def test_greater_than(self):
        filter = self.get_filter('gt', 3)
        self.assertEqual(filter, {
            'range': {
                'foo': {
                    'gt': 3
                }
            }
        })

    def test_greater_than_equal(self):
        filter = self.get_filter('gte', 3)
        self.assertEqual(filter, {
            'range': {
                'foo': {
                    'gte': 3
                }
            }
        })

    def test_literal_in_expression(self):
        with self.assertRaises(BadSpecError):
            FilterFactoryES.from_spec({
                'type': 'boolean_expression',
                'expression': 1,
                'operator': 'gt',
                'property_value': 2
            })

    def test_expression_in_value(self):
        with self.assertRaises(BadSpecError):
            FilterFactoryES.from_spec({
                'type': 'boolean_expression',
                'expression': {
                    'type': 'property_name',
                    'property_name': 'foo',
                },
                'operator': 'gt',
                'property_value': {
                    'type': 'property_name',
                    'property_name': 'bar',
                },
            })


class ConfigurableAndOrFilterTestMixin(object):
    filter_factory = None

    def get_filter(self, type_):
        return self.filter_factory.from_spec({
            "type": type_,
            "filters": [
                {
                    "type": "property_match",
                    "property_name": "foo",
                    "property_value": "bar"
                },
                {
                    "type": "property_match",
                    "property_name": "foo2",
                    "property_value": "bar2"
                }
            ]
        })


class ConfigurableANDFilterTest(ConfigurableAndOrFilterTestMixin, SimpleTestCase):
    filter_factory = FilterFactory

    def setUp(self):
        self.filter = self.get_filter('and')
        self.assertTrue(isinstance(self.filter, ANDFilter))

    def test_filter_match(self):
        self.assertTrue(self.filter(dict(foo='bar', foo2='bar2')))

    def test_filter_partial_match(self):
        self.assertFalse(self.filter(dict(foo='bar', foo2='not bar2')))

    def test_filter_no_match(self):
        self.assertFalse(self.filter(dict(foo='not bar', foo2='not bar2')))

    def test_filter_missing_partial_match(self):
        self.assertFalse(self.filter(dict(foo='bar')))

    def test_filter_missing_all(self):
        self.assertFalse(self.filter(dict(notfoo='not bar')))


class ConfigurableORFilterTest(ConfigurableAndOrFilterTestMixin, SimpleTestCase):
    filter_factory = FilterFactory

    def setUp(self):
        self.filter = self.get_filter('or')
        self.assertTrue(isinstance(self.filter, ORFilter))

    def test_filter_match(self):
        self.assertTrue(self.filter(dict(foo='bar', foo2='bar2')))

    def test_filter_partial_match(self):
        self.assertTrue(self.filter(dict(foo='bar', foo2='not bar2')))

    def test_filter_no_match(self):
        self.assertFalse(self.filter(dict(foo='not bar', foo2='not bar2')))

    def test_filter_missing_partial_match(self):
        self.assertTrue(self.filter(dict(foo='bar')))

    def test_filter_missing_all(self):
        self.assertFalse(self.filter(dict(notfoo='not bar')))


class ConfigurableAndOrFilterTest(ConfigurableAndOrFilterTestMixin, SimpleTestCase):
    filter_factory = FilterFactoryES

    def _test_filter(self, type_):
        self.assertEqual(self.get_filter(type_), {
            type_: (
                {'term': {'foo': 'bar'}},
                {'term': {'foo2': 'bar2'}},
            )
        })

    def test_and_filter(self):
        self._test_filter('and')

    def test_or_filter(self):
        self._test_filter('or')


class ComplexFilterTestMixin(object):
    filter_factory = None

    def setUp(self):
        # in slightly more compact format:
        # ((foo=bar) or (foo1=bar1 and foo2=bar2 and (foo3=bar3 or foo4=bar4)))
        self.filter = self.filter_factory.from_spec({
            "type": "or",
            "filters": [
                {
                    "type": "property_match",
                    "property_name": "foo",
                    "property_value": "bar"
                },
                {
                    "type": "and",
                    "filters": [
                        {
                            "type": "property_match",
                            "property_name": "foo1",
                            "property_value": "bar1"
                        },
                        {
                            "type": "property_match",
                            "property_name": "foo2",
                            "property_value": "bar2"
                        },
                        {
                            "type": "or",
                            "filters": [
                                {
                                    "type": "property_match",
                                    "property_name": "foo3",
                                    "property_value": "bar3"
                                },
                                {
                                    "type": "property_match",
                                    "property_name": "foo4",
                                    "property_value": "bar4"
                                }
                            ]
                        },
                    ]
                },
            ]
        })


class ComplexFilterTest(ComplexFilterTestMixin, SimpleTestCase):
    filter_factory = FilterFactory

    def test_complex_structure(self):
        # first level or
        self.assertTrue(self.filter(dict(foo='bar')))
        # first level and with both or's
        self.assertTrue(self.filter(dict(foo1='bar1', foo2='bar2', foo3='bar3')))
        self.assertTrue(self.filter(dict(foo1='bar1', foo2='bar2', foo4='bar4')))

        # first and not right
        self.assertFalse(self.filter(dict(foo1='not bar1', foo2='bar2', foo3='bar3')))
        # second and not right
        self.assertFalse(self.filter(dict(foo1='bar1', foo2='not bar2', foo3='bar3')))
        # last and not right
        self.assertFalse(self.filter(dict(foo1='bar1', foo2='bar2', foo3='not bar3', foo4='not bar4')))


class ComplexFilterTestES(ComplexFilterTestMixin, SimpleTestCase):
    filter_factory = FilterFactoryES

    def test_complex_structure(self):
        self.assertEqual(self.filter, {
            'or': (
                {'term': {'foo': 'bar'}},
                {'and': (
                    {'term': {'foo1': 'bar1'}},
                    {'term': {'foo2': 'bar2'}},
                    {'or': (
                        {'term': {'foo3': 'bar3'}},
                        {'term': {'foo4': 'bar4'}},
                    )}
                )}
            )
        })


class ConfigurableNOTFilterTestMixin(object):
    filter_factory = None

    def setUp(self):
        self.filter = self.filter_factory.from_spec({
            "type": "not",
            "filter": {
                "type": "property_match",
                "property_name": "foo",
                "property_value": "bar"
            }
        })


class ConfigurableNOTFilterTest(ConfigurableNOTFilterTestMixin, SimpleTestCase):
    filter_factory = FilterFactory

    def test_type(self):
        self.assertTrue(isinstance(self.filter, NOTFilter))

    def test_filter_match(self):
        self.assertTrue(self.filter(dict(foo='not bar')))

    def test_filter_no_match(self):
        self.assertFalse(self.filter(dict(foo='bar')))


class ConfigurableNOTFilterTestES(ConfigurableNOTFilterTestMixin, SimpleTestCase):
    filter_factory = FilterFactoryES

    def test_filter(self):
        self.assertEqual(self.filter, {
            'not': {
                'term': {'foo': 'bar'}
            }
        })


class ConfigurableNamedFilterTestMixin(object):
    filter_factory = None

    def setUp(self):
        self.filter = self.filter_factory.from_spec(
            {'type': 'named', 'name': 'foo'},
            FactoryContext({}, {
                'foo': self.filter_factory.from_spec({
                    "type": "not",
                    "filter": {
                        "type": "property_match",
                        "property_name": "foo",
                        "property_value": "bar"
                    }
                })
            })
        )


class ConfigurableNamedFilterTest(ConfigurableNamedFilterTestMixin, SimpleTestCase):
    filter_factory = FilterFactory

    def test_type(self):
        self.assertTrue(isinstance(self.filter, NOTFilter))

    def test_filter_match(self):
        self.assertTrue(self.filter(dict(foo='not bar')))

    def test_filter_no_match(self):
        self.assertFalse(self.filter(dict(foo='bar')))


class ConfigurableNamedFilterTestES(ConfigurableNamedFilterTestMixin, SimpleTestCase):
    filter_factory = FilterFactoryES

    def test_filter(self):
        self.assertEqual(self.filter, {
            'not': {
                'term': {'foo': 'bar'}
            }
        })
