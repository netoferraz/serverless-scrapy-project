from fastapi import FastAPI
from scrapy.utils.project import get_project_settings
import os
from twisted.internet import reactor
import scrapy.crawler as crawler
from scrapy.utils.log import configure_logging
from fuelstations.spiders.postos import FacilityDetails
from multiprocessing import Process, Queue
app = FastAPI()

def run_configuration(queue, spider, fstation_type, uf):
    try:
        settings = get_project_settings()
        settings_module_path = os.environ.get('SCRAPY_ENV', 'fuelstations.settings')
        settings.setmodule(settings_module_path)
        configure_logging(settings)
        runner = crawler.CrawlerRunner(settings)
        deferred = runner.crawl(spider, **{'fstation_type' : fstation_type, 'uf' : uf})
        deferred.addBoth(lambda _: reactor.stop())
        reactor.run()
        queue.put(None)
    except Exception as e:
        queue.put(e)

def run_spider(spider, fstation_type, uf):
    q = Queue()
    p = Process(target=run_configuration, args=(q, spider, fstation_type, uf))
    p.start()
    result = q.get()
    p.join()

    if result is not None:
        raise result

@app.post("/crawler")
def iniciar(fstation_type: str, uf:str):
    """[summary]

    Parameters
    ----------
    fstation_type : str
        fuel station type
    uf : str
        federative unit of Brazil
    """
    if uf not in ["AC", "AL", "AM", "AP", "BA", "CE", "DF",
		"ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB",
		"PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
		"SE", "SP", "TO"]:
        return {'error' : f"{uf} isn't a valid UF."}
    if fstation_type not in ["All", "Revendedor", "Abastecimento", "Escola", "GNV", "Flutuante", "Aviação", '"Marítimo']:
        return {'error' : f"{fstation_type} isn't a valid fstation_type."}
    run_spider(FacilityDetails, fstation_type, uf)
    return 'OK'