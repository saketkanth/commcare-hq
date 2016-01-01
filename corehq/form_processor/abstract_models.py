import json
from collections import defaultdict
from copy import copy
import logging
from abc import ABCMeta, abstractmethod, abstractproperty

import itertools
import six as six
from couchdbkit import ResourceNotFound

from dimagi.utils.decorators.memoized import memoized

logger = logging.getLogger('phone.models')  # TODO: Probably call this something else...

class AbstractXFormInstance(object):

    # @property
    # def form_id(self):
    #     raise NotImplementedError()

    @property
    def form_data(self):
        raise NotImplementedError()

    @property
    def metadata(self):
        raise NotImplementedError()

    @property
    def is_normal(self):
        raise NotImplementedError()

    @property
    def is_archived(self):
        raise NotImplementedError()

    @property
    def is_deprecated(self):
        raise NotImplementedError()

    @property
    def is_duplicate(self):
        raise NotImplementedError()

    @property
    def is_error(self):
        raise NotImplementedError()

    @property
    def is_submission_error_log(self):
        raise NotImplementedError()

    def auth_context(self):
        raise NotImplementedError()

    def get_data(self, xpath):
        raise NotImplementedError()

    def get_attachment(self, attachment_name):
        raise NotImplementedError()

    def archive(self, user_id=None):
        raise NotImplementedError()

    def unarchive(self, user_id=None):
        raise NotImplementedError()

    def get_xml_element(self):
        raise NotImplementedError()

    def get_xml(self):
        raise NotImplementedError()

    def save(self, *args, **kwargs):
        raise NotImplementedError()

    def set_submission_properties(self, submission_post):
        raise NotImplementedError()

    def to_json(self):
        raise NotImplementedError()

    @classmethod
    def get(self, xform_id):
        raise NotImplementedError()

    @memoized
    def get_sync_token(self):
        from casexml.apps.phone.models import get_properly_wrapped_sync_log
        if self.last_sync_token:
            try:
                return get_properly_wrapped_sync_log(self.last_sync_token)
            except ResourceNotFound:
                logging.exception('No sync token with ID {} found. Form is {} in domain {}'.format(
                    self.last_sync_token, self.form_id, self.domain,
                ))
                raise
        return None


class AbstractCommCareCase(object):

    # @property
    # def case_id(self):
    #     raise NotImplementedError()

    @property
    def case_name(self):
        raise NotImplementedError()

    def soft_delete(self):
        raise NotImplementedError()

    def get_attachment(self, attachment_name):
        raise NotImplementedError()

    def is_deleted(self):
        raise NotImplementedError()

    def to_xml(self, version, include_case_on_closed=False):
        raise NotImplementedError()

    def dynamic_case_properties(self):
        raise NotImplementedError()

    def get_actions_for_form(self, xform):
        raise NotImplementedError

    def modified_since_sync(self, sync_log):
        raise NotImplementedError


class AbstractIndexTree(object):
    """
    Document type representing a case dependency tree
    """

    def __repr__(self):
        return json.dumps(self.indices, indent=2)

    @staticmethod
    def get_all_dependencies(case_id, child_index_tree, extension_index_tree, closed_cases=None,
                             cached_child_map=None, cached_extension_map=None):
        """Takes a child and extension index tree and returns returns a set of all dependencies of <case_id>

        Traverse each incoming index, return each touched case. Stop traversing
        incoming extensions if they lead to closed cases.
        Traverse each outgoing index in the extension tree, return each touched case
        """
        if closed_cases is None:
            closed_cases = set()

        def _recursive_call(case_id, all_cases, cached_child_map, cached_extension_map):
            all_cases.add(case_id)
            incoming_extension_indices = extension_index_tree.get_cases_that_directly_depend_on_case(
                case_id,
                cached_map=cached_extension_map
            )
            open_incoming_extension_indices = {
                case for case in incoming_extension_indices if case not in closed_cases
            }
            all_incoming_indices = itertools.chain(
                child_index_tree.get_cases_that_directly_depend_on_case(case_id, cached_map=cached_child_map),
                open_incoming_extension_indices,
            )

            for dependent_case in all_incoming_indices:
                # incoming indices
                if dependent_case not in all_cases:
                    all_cases.add(dependent_case)
                    _recursive_call(dependent_case, all_cases, cached_child_map, cached_extension_map)
            for indexed_case in extension_index_tree.indices.get(case_id, {}).values():
                # outgoing extension indices
                if indexed_case not in all_cases:
                    all_cases.add(indexed_case)
                    _recursive_call(indexed_case, all_cases, cached_child_map, cached_extension_map)

        all_cases = set()
        cached_child_map = cached_child_map or _reverse_index_map(child_index_tree.indices)
        cached_extension_map = cached_extension_map or _reverse_index_map(extension_index_tree.indices)
        _recursive_call(case_id, all_cases, cached_child_map, cached_extension_map)
        return all_cases

    @staticmethod
    def get_all_outgoing_cases(case_id, child_index_tree, extension_index_tree):
        """traverse all outgoing child and extension indices"""
        all_cases = set([case_id])
        new_cases = set([case_id])
        while new_cases:
            case_to_check = new_cases.pop()
            parent_cases = set(child_index_tree.indices.get(case_to_check, {}).values())
            host_cases = set(extension_index_tree.indices.get(case_to_check, {}).values())
            new_cases = (new_cases | parent_cases | host_cases) - all_cases
            all_cases = all_cases | parent_cases | host_cases
        return all_cases

    @staticmethod
    def traverse_incoming_extensions(case_id, extension_index_tree, closed_cases, cached_map=None):
        """traverse open incoming extensions"""
        all_cases = set([case_id])
        new_cases = set([case_id])
        cached_map = cached_map or _reverse_index_map(extension_index_tree.indices)
        while new_cases:
            case_to_check = new_cases.pop()
            open_incoming_extension_indices = {
                case for case in
                extension_index_tree.get_cases_that_directly_depend_on_case(case_to_check,
                                                                            cached_map=cached_map)
                if case not in closed_cases
            }
            for incoming_case in open_incoming_extension_indices:
                new_cases.add(incoming_case)
                all_cases.add(incoming_case)
        return all_cases

    def get_cases_that_directly_depend_on_case(self, case_id, cached_map=None):
        cached_map = cached_map or _reverse_index_map(self.indices)
        return cached_map.get(case_id, [])

    def get_all_cases_that_depend_on_case(self, case_id, cached_map=None):
        """
        Recursively builds a tree of all cases that depend on this case and returns
        a flat set of case ids.

        Allows passing in a cached map of reverse index references if you know you are going
        to call it more than once in a row to avoid rebuilding that.
        """

        def _recursive_call(case_id, all_cases, cached_map):
            all_cases.add(case_id)
            for dependent_case in self.get_cases_that_directly_depend_on_case(case_id, cached_map=cached_map):
                if dependent_case not in all_cases:
                    all_cases.add(dependent_case)
                    _recursive_call(dependent_case, all_cases, cached_map)

        all_cases = set()
        cached_map = cached_map or _reverse_index_map(self.indices)
        _recursive_call(case_id, all_cases, cached_map)
        return all_cases

    def delete_index(self, from_case_id, index_name):
        prior_ids = self.indices.pop(from_case_id, {})
        prior_ids.pop(index_name, None)
        if prior_ids:
            self.indices[from_case_id] = prior_ids

    def set_index(self, from_case_id, index_name, to_case_id):
        prior_ids = self.indices.get(from_case_id, {})
        prior_ids[index_name] = to_case_id
        self.indices[from_case_id] = prior_ids

    def apply_updates(self, other_tree):
        """
        Apply updates from another IndexTree and return a copy with those applied.

        If an id is found in the new one, use that id's indices, otherwise, use this ones,
        (defaulting to nothing).
        """
        assert isinstance(other_tree, self.__class__)
        new = self.__class__(
            indices=copy(self.indices),
        )
        new.indices.update(other_tree.indices)
        return new

class AbstractSyncLog(object):

    def to_json(self):
        raise NotImplementedError


class AbstractLedgerValue(six.with_metaclass(ABCMeta)):
    @abstractproperty
    def case_id(self):
        pass

    @abstractproperty
    def section_id(self):
        pass

    @abstractproperty
    def entry_id(self):
        pass

    @abstractproperty
    def balance(self):
        pass


class AbstractSupplyInterface(six.with_metaclass(ABCMeta)):
    @classmethod
    @abstractmethod
    def get_by_location(cls, location):
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def get_or_create_by_location(cls, location):
        raise NotImplementedError
