import scrapy
from scrapy.http import FormRequest
from fuelstations.items import FacilityDetails
import datetime
from w3lib.html import remove_tags
from dateparser import parse
from scrapy.exceptions import NotConfigured


class FacilityDetailsSpider(scrapy.Spider):
    name = "details"
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
        "ITEM_PIPELINES": {"fuelstations.pipelines.BQIngestor": 200},
    }

    def __init__(self, **kwargs):
        codes = kwargs.get("codes", None)
        if not codes:
            raise NotConfigured("codes parameter has needed to be set.")
        self.codes = codes
        if isinstance(self.codes, str):
            self.codes = self.codes.split(",")
        if not isinstance(self.codes, list):
            raise NotConfigured("codes parameter must be a list of strings.")
        uf = kwargs.get("uf", None)
        if not uf:
            raise NotConfigured("uf parameter has needed to be set.")
        self.uf = uf
        self.logger.info(
            f"{self.__class__.name} has started with: {self.codes} and {self.uf}."
        )

    def start_requests(self):
        for code in self.codes:
            # self.logger.info(f"Preparing POST request for {code}.")
            yield FormRequest(
                "https://postos.anp.gov.br/resultado.asp",
                method="POST",
                formdata={"Cod_Inst": code, "estado": self.uf, "municipio": "0"},
                dont_filter=True,
                callback=self.parse,
                cb_kwargs={"cod_inst": code},
            )

    def text_cleaning(self, text):
        text = remove_tags(text)
        text = text.replace("\xa0", "")
        text = text.strip()
        return text

    def parse(self, response, cod_inst):
        self.logger.info(
            f"[{self.uf}] Collecting data from fuel station with installation code number {cod_inst}."
        )
        equipament_container = []
        fstation_data = FacilityDetails()
        for el in response.xpath("//table"):
            width = el.attrib.get("width", None)
            if width == "760":
                get_feature = None
                for elem in el.css("table"):
                    height_table = elem.attrib.get("height", None)
                    width_table = elem.attrib.get("width", None)
                    if height_table != "530":
                        if width_table == "634":
                            for line in elem.css("tr td"):
                                for fontline in line.css("font"):
                                    cod_status_posto = fontline.attrib.get("size")
                                    if cod_status_posto == "3":
                                        status_posto = self.text_cleaning(
                                            fontline.get()
                                        )
                                        fstation_data["status_posto"] = status_posto
                                which_feature = line.attrib.get("align")
                                if which_feature == "right":
                                    for header in line.css("b"):
                                        header_text = self.text_cleaning(header.get())
                                        get_feature = self.feature_mapping.get(
                                            header_text, None
                                        )
                                elif which_feature == "left":
                                    for value in line.css("font"):
                                        value_text = self.text_cleaning(value.get())
                                        if get_feature:
                                            if get_feature == "municipio_uf":
                                                city, uf = value_text.split("/")
                                                fstation_data[
                                                    "municipio"
                                                ] = self.text_cleaning(city)
                                                fstation_data[
                                                    "uf"
                                                ] = self.text_cleaning(uf)
                                            elif get_feature == "bandeira_inicio":
                                                try:
                                                    (
                                                        brand,
                                                        brand_start_date,
                                                    ) = value_text.split("/")
                                                except ValueError:
                                                    (
                                                        brand,
                                                        brand_start_date,
                                                    ) = value_text.split("-")
                                                finally:
                                                    fstation_data[
                                                        "bandeira"
                                                    ] = self.text_cleaning(brand)
                                                    fstation_data["bandeira_inicio"] = (
                                                        parse(
                                                            self.text_cleaning(
                                                                brand_start_date
                                                            ),
                                                            languages=["pt"],
                                                        )
                                                        .date()
                                                        .isoformat()
                                                    )
                                            else:
                                                if get_feature == "data_publicacao":
                                                    fstation_data[get_feature] = (
                                                        parse(
                                                            self.text_cleaning(
                                                                value_text
                                                            ),
                                                            languages=["pt"],
                                                        )
                                                        .date()
                                                        .isoformat()
                                                    )
                                                else:
                                                    fstation_data[
                                                        get_feature
                                                    ] = self.text_cleaning(value_text)
                        if width_table == "644":
                            equipamento = {}
                            for line in elem.css("tr td"):
                                which_feature = line.attrib.get("width")
                                if which_feature == "450":
                                    for value in line.css("font"):
                                        value_text = self.text_cleaning(value.get())
                                        if (
                                            value_text != "Produtos:"
                                            and value_text != "Tancagem (m³):"
                                            and value_text != "Bicos:"
                                        ):
                                            equipamento["produto"] = value_text
                                elif which_feature == "103":
                                    for value in line.css("font"):
                                        value_text = self.text_cleaning(value.get())
                                        if (
                                            value_text != "Produtos:"
                                            and value_text != "Tancagem (m³):"
                                            and value_text != "Bicos:"
                                        ):
                                            equipamento["tancagem"] = float(
                                                value_text.replace(",", ".")
                                            )
                                elif which_feature == "92":
                                    for value in line.css("font"):
                                        value_text = self.text_cleaning(value.get())
                                        if (
                                            value_text != "Produtos:"
                                            and value_text != "Tancagem (m³):"
                                            and value_text != "Bicos:"
                                        ):
                                            equipamento["bicos"] = float(
                                                value_text.replace(",", ".")
                                            )
                                if (
                                    equipamento.get("produto", "") != ""
                                    and equipamento.get("tancagem", "") != ""
                                    and equipamento.get("bicos", "") != ""
                                ):
                                    equipament_container.append(equipamento)
                                    equipamento = {}

        fstation_data["equipamentos"] = equipament_container
        fstation_data["datetime_collected"] = datetime.datetime.utcnow().isoformat()
        yield fstation_data
