import datetime
import logging

from celery import chord, chain
from django.apps import apps
from django.conf import settings
from django.core.management import BaseCommand
from django_elasticsearch_dsl.registries import registry

from ...tasks import (index_objects_to_es_task, switch_es_index_task, create_new_es_index_task,
                      index_missing_objects_task)
from ...utils import chunks

log = logging.getLogger(__name__)


class Command(BaseCommand):

    @staticmethod
    def _get_indexing_tasks(app_label, model_name, instance_ids, document_class, index_name):
        chunk_objects = chunks(instance_ids, settings.ES_TASK_CHUNK_SIZE)

        for chunk in chunk_objects:
            data = {
                'app_label': app_label,
                'model_name': model_name,
                'document_class': document_class,
                'index_name': index_name,
                'objects_id': chunk
            }
            yield index_objects_to_es_task.si(**data)

    def _run_reindex_tasks(self, models):
        for doc in registry.get_documents(models):
            qs = doc().get_queryset()
            instance_ids = list(qs.values_list('id', flat=True))

            app_label = qs.model._meta.app_label
            model_name = qs.model.__name__

            index_name = doc._doc_type.index
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            new_index_name = "{}_{}".format(index_name, timestamp)

            pre_index_task = create_new_es_index_task.si(app_label=app_label,
                                                         model_name=model_name,
                                                         index_name=index_name,
                                                         new_index_name=new_index_name)

            indexing_tasks = self._get_indexing_tasks(app_label=app_label, model_name=model_name,
                                                      instance_ids=instance_ids,
                                                      document_class=str(doc),
                                                      index_name=new_index_name)

            post_index_task = switch_es_index_task.si(app_label=app_label, model_name=model_name,
                                                      index_name=index_name,
                                                      new_index_name=new_index_name)

            # Task to run in order to add the objects
            # that has been inserted into database while indexing_tasks was running
            missed_index_task = index_missing_objects_task.si(app_label=app_label,
                                                              model_name=model_name,
                                                              document_class=str(doc),
                                                              indexed_instance_ids=instance_ids)

            # http://celery.readthedocs.io/en/latest/userguide/canvas.html#chords
            chord_tasks = chord(header=indexing_tasks, body=post_index_task)
            # http://celery.readthedocs.io/en/latest/userguide/canvas.html#chain
            chain(pre_index_task, chord_tasks, missed_index_task).apply_async()

            message = ("Successfully issued tasks for {}.{}, total {} items"
                       .format(app_label, model_name, len(instance_ids)))
            log.info(message)

    def add_arguments(self, parser):
        parser.add_argument(
            '--models',
            dest='models',
            type=str,
            nargs='*',
            help=("Specify the model to be updated in elasticsearch."
                  "The format is <app_label>.<model_name>")
        )

    def handle(self, *args, **options):
        """
        Index models into Elasticsearch index asynchronously using celery.

        You can specify model to get indexed by passing
        `--model <app_label>.<model_name>` parameter.
        Otherwise, it will reindex all the models
        """
        models = None
        if options['models']:
            models = [apps.get_model(model_name) for model_name in options['models']]

        self._run_reindex_tasks(models=models)