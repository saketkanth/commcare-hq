from .interface import PillowProcessor
from corehq.apps.app_manager.dbaccessors import get_app
from corehq.util.quickcache import quickcache


class FormProcessor(PillowProcessor):
    """
    Pillow used to process each form and make updates if necessary
    """

    def process_change(self, pillow_instance, change):
        if change.deleted and change.id:
            return
        doc = change.get_document()
        if not doc:
            return

        build_id = doc.get('build_id')
        domain = change.get_document().get('domain')

        if not build_id or not domain:
            app = self._get_app(domain, build_id)
            app.has_submissions = True
            app.save()
            return

    @quickcache(['domain', 'build_id'], timeout=60 * 60)
    def _get_app(self, domain, build_id):
        return get_app(domain, build_id)
