import os
from pathlib import Path
import sys
from itemadapter import ItemAdapter
from google.cloud import bigquery
from google.cloud import pubsub_v1
import json


class PubSubPublisher:
    def __init__(self, project_name, topic_id, credentials_path) -> None:
        try:
            credentials_file = Path(credentials_path)
        except TypeError:
            credentials_file = os.environ.get("GCP_CREDENTIALS_PUBSUB")
        else:
            if not credentials_file.is_file():
                print("File credentials for PubSub not found.")
                sys.exit(1)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_file)
            self.project_name = project_name
            self.topic_id = topic_id

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            project_name=crawler.settings.get("GCP_PROJECT_ID"),
            topic_id=crawler.settings.get("PUBSUB_TOPIC_ID"),
            credentials_path=crawler.settings.get("GCP_CREDENTIALS_PUBSUB"),
        )

    def open_spider(self, spider):
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(self.project_name, self.topic_id)

    def process_item(self, item, spider):
        payload = ItemAdapter(item).asdict()
        payload = json.dumps(payload).encode("utf-8")
        future = self.publisher.publish(self.topic_path, payload, origin="task_maker")
        _id = future.result()
        spider.logger.info(f"Message {_id} has sent for topic {self.topic_id}.")


class BQIngestor:
    def __init__(self, project_name, bq_table, credentials_path):
        try:
            credentials_file = Path(credentials_path)
        except TypeError:
            credentials_file = os.environ.get("GCP_CREDENTIALS_BQ")
        if not credentials_file.is_file():
            print("File credentials not found.")
            sys.exit(1)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_file)
        self.project_name = project_name
        self.bq_table = bq_table

    def open_spider(self, spider):
        self.bq_client = bigquery.Client(project=self.project_name)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            project_name=crawler.settings.get("GCP_PROJECT_ID"),
            bq_table=crawler.settings.get("BQ_TABLE"),
            credentials_path=crawler.settings.get("GCP_CREDENTIALS_BQ"),
        )

    def process_item(self, item, spider):
        payload = ItemAdapter(item).asdict()
        payload = [payload]
        errors = self.bq_client.insert_rows_json(
            self.bq_table, payload, row_ids=[None] * len(payload)
        )
        if errors == []:
            spider.logger.info(
                f"We've scraped sucessly data for fuel station {item.get('cnpj')}."
            )
        else:
            spider.logger.error(
                "Encountered errors while inserting rows: {}".format(errors)
            )
            spider.logger.error(payload)
