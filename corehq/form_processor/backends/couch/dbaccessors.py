from couchdbkit import ResourceNotFound

from casexml.apps.case.dbaccessors import get_extension_case_ids, \
    get_indexed_case_ids, get_all_reverse_indices_info
from casexml.apps.case.models import CommCareCase
from casexml.apps.case.util import get_case_xform_ids
from casexml.apps.phone.exceptions import InvalidSyncLogException
from casexml.apps.phone.models import SyncLog, get_properly_wrapped_sync_log, \
    SimplifiedSyncLog, LOG_FORMAT_SIMPLIFIED
from corehq.apps.hqcase.dbaccessors import get_case_ids_in_domain
from corehq.apps.hqcase.dbaccessors import (
    get_open_case_ids,
    get_closed_case_ids,
    get_case_ids_in_domain_by_owner
)
from corehq.dbaccessors.couchapps.cases_by_server_date.by_owner_server_modified_on import \
    get_case_ids_modified_with_owner_since
from corehq.dbaccessors.couchapps.cases_by_server_date.by_server_modified_on import \
    get_last_modified_dates
from corehq.form_processor.exceptions import SyncLogNotFound
from corehq.form_processor.interfaces.dbaccessors import AbstractCaseAccessor, AbstractFormAccessor, \
    AbstractSyncLogAccessor
from couchforms.dbaccessors import get_forms_by_type
from couchforms.models import XFormInstance, doc_types
from dimagi.utils.couch.database import iter_docs, get_safe_write_kwargs


class FormAccessorCouch(AbstractFormAccessor):
    @staticmethod
    def get_form(form_id):
        return XFormInstance.get(form_id)

    @staticmethod
    def get_forms_by_type(domain, type_, limit, recent_first=False):
        return get_forms_by_type(domain, type_, recent_first, limit)

    @staticmethod
    def get_with_attachments(form_id):
        doc = XFormInstance.get_db().get(form_id, attachments=True)
        return doc_types()[doc['doc_type']].wrap(doc)

    @staticmethod
    def save_new_form(form):
        form.save()

    @staticmethod
    def update_form_problem_and_state(form):
        form.save()


class CaseAccessorCouch(AbstractCaseAccessor):

    @staticmethod
    def get_case(case_id):
        return CommCareCase.get(case_id)

    @staticmethod
    def get_cases(case_ids, ordered=False):
        return [
            CommCareCase.wrap(doc) for doc in iter_docs(
                CommCareCase.get_db(),
                case_ids
            )
        ]

    @staticmethod
    def get_case_xform_ids(case_id):
        return get_case_xform_ids(case_id)

    @staticmethod
    def get_case_ids_in_domain(domain, type=None):
        return get_case_ids_in_domain(domain, type=type)

    @staticmethod
    def get_case_ids_in_domain_by_owners(domain, owner_ids):
        return get_case_ids_in_domain_by_owner(domain, owner_id__in=owner_ids)

    @staticmethod
    def get_open_case_ids(domain, owner_id):
        return get_open_case_ids(domain, owner_id)

    @staticmethod
    def get_closed_case_ids(domain, owner_id):
        return get_closed_case_ids(domain, owner_id)

    @staticmethod
    def get_case_ids_modified_with_owner_since(domain, owner_id, reference_date):
        return get_case_ids_modified_with_owner_since(domain, owner_id, reference_date)

    @staticmethod
    def get_extension_case_ids(domain, case_ids):
        return get_extension_case_ids(domain, case_ids)

    @staticmethod
    def get_indexed_case_ids(domain, case_ids):
        return get_indexed_case_ids(domain, case_ids)

    @staticmethod
    def get_last_modified_dates(domain, case_ids):
        return get_last_modified_dates(domain, case_ids)

    @staticmethod
    def get_all_reverse_indices_info(domain, case_ids):
        return get_all_reverse_indices_info(domain, case_ids)


class SyncLogAccessorCouch(AbstractSyncLogAccessor):

    @staticmethod
    def save_new_sync_log(**kwargs):
        # TODO: pass previous_log_rev, and last_seq to this function
        new_sync_log = SyncLog(**kwargs)
        new_sync_log.save(**get_safe_write_kwargs())
        return new_sync_log

    @staticmethod
    def save_sync_log(sync_log):
        return sync_log.save()

    @staticmethod
    def get_sync_log(sync_log_id):
        try:
            sync_log = get_properly_wrapped_sync_log(sync_log_id)
        except ResourceNotFound:
            raise SyncLogNotFound
        if sync_log.doc_type != 'SyncLog':
            raise InvalidSyncLogException('Bad sync log doc type for {}'.format(sync_log_id))
        return sync_log

    @staticmethod
    def convert_sync_log_type(sync_log, desired_type):
        # convert to the right type if necessary
        if not isinstance(sync_log, desired_type):
            # this call can fail with an IncompatibleSyncLogType error
            sync_log = desired_type.from_other_format(sync_log)
        return sync_log

    @staticmethod
    def update_sync_log_format(sync_log):
        # update sync token - marking it as the new format
        new_sync_log = SimplifiedSyncLog.wrap(sync_log.to_json())
        new_sync_log.log_format = LOG_FORMAT_SIMPLIFIED
        return new_sync_log
