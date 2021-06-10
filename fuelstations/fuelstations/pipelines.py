# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
from pathlib import Path
import sys
from itemadapter import ItemAdapter
from google.cloud import bigquery

class BQIngestor:
    def __init__(
        self,
        project_name,
        bq_table,
    ):
        self.project_name = project_name
        self.bq_table = bq_table
        credentials_file = Path(os.environ.get("GCP_CREDENTIALS", "./fuelstations/credentials/credentials.json"))
        if not credentials_file.is_file():
            self.logger.error("File credentials not found.")
            sys.exit(1)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_file)
    
    def open_spider(self, spider):
        self.bq_client = bigquery.Client(project=self.project_name)


    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            project_name=crawler.settings.get("GCP_PROJECT_ID"),
            bq_table=crawler.settings.get("BQ_TABLE"),
        )

    def process_item(self, item, spider):
        payload = ItemAdapter(item).asdict()
        payload = [payload]
        errors = self.bq_client.insert_rows_json(
            self.bq_table, payload, row_ids=[None] * len(payload)
        )
        if errors == []:
            spider.logger.debug(f"We've scraped sucessly data for fuel station {item.get('cnpj')}.")
        else:
            spider.logger.error("Encountered errors while inserting rows: {}".format(errors))
            print(payload)
