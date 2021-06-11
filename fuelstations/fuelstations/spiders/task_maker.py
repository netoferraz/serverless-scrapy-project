import scrapy
from scrapy import Request
from scrapy.http import FormRequest
from typing import List
from fuelstations.items import FacilityCodes
from scrapy.exceptions import NotConfigured


class TaskMakerSpider(scrapy.Spider):
    name = "tasks"
    start_urls = ["http://postos.anp.gov.br/"]
    fstation_codes = {
        "All": "0",
        "Revendedor": "1",
        "Abastecimento": "2",
        "Escola": "3",
        "GNV": "4",
        "Flutuante": "5",
        "Aviação": "6",
        "Marítimo": "7",
    }
    feature_mapping = {
        "Autorização:": "autorizacao",
        "CNPJ/CPF:": "cnpj",
        "Razão Social:": "razao_social",
        "Nome Fantasia:": "nome_fantasia",
        "Endereço:": "endereco",
        "complemento": "complemento",
        "Bairro:": "bairro",
        "Município/UF:": "municipio_uf",
        "CEP:": "cep",
        "Número Despacho:": "numero_despacho",
        "Data Publicação:": "data_publicacao",
        "Bandeira/Início:": "bandeira_inicio",
        "Tipo do Posto:": "tipo_posto",
        "Sócios:": "socios",
    }

    custom_settings = {
        "ITEM_PIPELINES": {"fuelstations.pipelines.PubSubPublisher": 200},
    }

    def __init__(self, **kwargs):
        # super().__init__(**kwargs)
        fstation_type = kwargs.get("fstation_type", None)
        if not fstation_type:
            raise NotConfigured("fstation_type parameter has needed to be set.")

        self.fstation_type = fstation_type
        uf = kwargs.get("uf", None)
        if not uf:
            raise NotConfigured("uf parameter has needed to be set.")
        self.uf = uf
        self.logger.debug(
            f"Crawler has started with: {self.fstation_type} and {self.uf}."
        )

    def start_requests(self):
        for url in self.start_urls:
            yield Request(
                url,
                callback=self.parse,
                dont_filter=True,
                meta={"dont_redirect": True, "handle_httpstatus_list": [302]},
            )

    def chunks(self, lst: List, n: int):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    def parse(self, response):
        yield FormRequest(
            url="https://postos.anp.gov.br/consulta.asp",
            method="POST",
            formdata={
                "sCnpj": "",
                "sRazaoSocial": "",
                "sEstado": self.uf,
                "sMunicipio": "0",
                "sBandeira": "0",
                "sProduto": "0",
                "sTipodePosto": self.fstation_codes.get(self.fstation_type, 0),
                "p": "",
                "hPesquisar": "PESQUISAR",
            },
            callback=self.parse_form,
            dont_filter=True,
            cb_kwargs={"p": ""},
        )

    def parse_form(self, response, p: str):
        if p == "":
            self.logger.info(f"[{self.uf}] Visiting page number 1.")
        else:
            self.logger.info(f"[{self.uf}] Visiting page number {p}.")
        facility_codes = response.xpath(
            "//input[contains(@onclick, 'jogaform')]/@onclick"
        ).re(r"\d+")
        if facility_codes:
            fcode_chunks = self.chunks(facility_codes, 25)
            for codes in fcode_chunks:
                codeItem = FacilityCodes()
                codeItem["codes"] = codes
                codeItem["uf"] = self.uf
                yield codeItem
        # check pagination
        pagination_form = response.xpath("//form[@name='formNext']").get()
        if pagination_form:
            pag = response.xpath(
                "//form[@name='formNext']//following-sibling::input/@onclick"
            ).re(r"\d+")[0]
            headers = {
                "Connection": "keep-alive",
                "Cache-Control": "max-age=0",
                "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
                "sec-ch-ua-mobile": "?0",
                "Upgrade-Insecure-Requests": "1",
                "Origin": "https://postos.anp.gov.br",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document",
                "Referer": "https://postos.anp.gov.br/consulta.asp",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            yield FormRequest(
                url="https://postos.anp.gov.br/consulta.asp",
                method="POST",
                headers=headers,
                formdata={
                    "sCnpj": "",
                    "sRazaoSocial": "",
                    "sEstado": self.uf,
                    "sMunicipio": "0",
                    "sBandeira": "0",
                    "sProduto": "0",
                    "sTipodePosto": self.fstation_codes.get(self.fstation_type, 0),
                    "p": pag,
                    "hPesquisar": "PESQUISAR",
                },
                callback=self.parse_form,
                dont_filter=True,
                cb_kwargs={"p": pag},
            )
        else:
            if not p:
                self.logger.info(f"[{self.uf}] There aren't results to collect.")
            else:
                self.logger.info(f"[{self.uf}] There are no more pages to visit.")
