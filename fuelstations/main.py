from fastapi import FastAPI, HTTPException
from scrapy.utils.project import get_project_settings
import os
import scrapy.crawler as crawler
from scrapy.utils.log import configure_logging
from fuelstations.spiders import FacilityDetailsSpider, TaskMakerSpider
from pydantic import BaseModel
from typing import Dict
import json
import base64
import crochet

crochet.setup()


class PubSubMessage(BaseModel):
    message: Dict
    subscription: str


app = FastAPI()


@crochet.run_in_reactor
@app.post("/taskmaker")
def gen_task(fstation_type: str, uf: str):
    """[summary]

    Parameters
    ----------
    fstation_type : str
        fuel station type
    uf : str
        federative unit of Brazil
    """
    if uf not in [
        "AC",
        "AL",
        "AM",
        "AP",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MG",
        "MS",
        "MT",
        "PA",
        "PB",
        "PE",
        "PI",
        "PR",
        "RJ",
        "RN",
        "RO",
        "RR",
        "RS",
        "SC",
        "SE",
        "SP",
        "TO",
    ]:
        raise HTTPException(status_code=404, detail=f"{uf} isn't a valid UF.")

    if fstation_type not in [
        "All",
        "Revendedor",
        "Abastecimento",
        "Escola",
        "GNV",
        "Flutuante",
        "Aviação",
        '"Marítimo',
    ]:
        raise HTTPException(
            status_code=404, detail=f"{fstation_type} isn't a valid fstation_type."
        )
    settings = get_project_settings()
    settings_module_path = os.environ.get("SCRAPY_ENV", "fuelstations.settings")
    settings.setmodule(settings_module_path)
    configure_logging(settings)
    runner = crawler.CrawlerRunner(settings)
    _ = runner.crawl(TaskMakerSpider, **{"fstation_type": fstation_type, "uf": uf})
    return {"status": "TaskMakerSpider has started."}


@crochet.run_in_reactor
@app.post("/details")
def collect_details(data: PubSubMessage):
    message = data.message
    # base64
    b64payload = message.get("data")
    payload = json.loads(base64.b64decode(b64payload).decode("utf-8"))
    codes = payload.get("codes")
    uf = payload.get("uf")
    if not codes:
        raise HTTPException(status_code=404, detail="codes not found.")
    if not uf:
        raise HTTPException(status_code=404, detail="uf not found.")
    settings = get_project_settings()
    settings_module_path = os.environ.get("SCRAPY_ENV", "fuelstations.settings")
    settings.setmodule(settings_module_path)
    configure_logging(settings)
    runner = crawler.CrawlerRunner(settings)
    _ = runner.crawl(FacilityDetailsSpider, **{"codes": codes, "uf": uf})
    return {"status": "FacilityDetailsSpider has started."}
