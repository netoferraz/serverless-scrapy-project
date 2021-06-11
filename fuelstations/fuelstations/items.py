# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class FacilityDetails(scrapy.Item):
    autorizacao = scrapy.Field()
    cnpj = scrapy.Field()
    razao_social = scrapy.Field()
    nome_fantasia = scrapy.Field()
    endereco = scrapy.Field()
    complemento = scrapy.Field()
    bairro = scrapy.Field()
    municipio = scrapy.Field()
    uf = scrapy.Field()
    cep = scrapy.Field()
    numero_despacho = scrapy.Field()
    data_publicacao = scrapy.Field()
    bandeira = scrapy.Field()
    bandeira_inicio = scrapy.Field()
    tipo_posto = scrapy.Field()
    status_posto = scrapy.Field()
    socios = scrapy.Field()
    equipamentos = scrapy.Field()
    datetime_collected = scrapy.Field()


class FacilityCodes(scrapy.Item):
    codes = scrapy.Field()
    uf = scrapy.Field()
