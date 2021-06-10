import scrapy
from scrapy import Request
from scrapy.http import FormRequest
from w3lib.html import remove_tags
from fuelstations.items import PostoDetails
import datetime
from dateparser import parse

class FacilityDetails(scrapy.Spider):
    name = 'postos'
    start_urls = ['http://postos.anp.gov.br/']
    mapeamento_tipo_posto = {"All" : "0", "Revendedor" : "1", "Abastecimento" : "2", "Escola" : "3", "GNV" : "4", "Flutuante" : "5", "Aviação" : "6", "Marítimo" : "7"}
    mapeamento_features = {
        "Autorização:" : "autorizacao",
        'CNPJ/CPF:' : 'cnpj',
        'Razão Social:' : 'razao_social',
        'Nome Fantasia:' : 'nome_fantasia',
        'Endereço:' : 'endereco',
        'complemento' : 'complemento',
        'Bairro:' : 'bairro',
        'Município/UF:' : 'municipio_uf',
        "CEP:" : 'cep',
        "Número Despacho:" : "numero_despacho",
        "Data Publicação:" : "data_publicacao",
        "Bandeira/Início:" : "bandeira_inicio",	
        "Tipo do Posto:" : "tipo_posto",
        "Sócios:" : "socios"
    }
    def start_requests(self):
        for url in self.start_urls:
            yield Request(
                url, 
                callback=self.parse, 
                dont_filter=True, 
                meta={
                'dont_redirect': True,
                'handle_httpstatus_list': [302]
                }
            )

    def text_cleaning(self, text):
        text = remove_tags(text)
        text = text.replace("\xa0", "")
        text = text.strip()
        return text
    
    def parse(self, response):
        yield FormRequest(
            url='https://postos.anp.gov.br/consulta.asp', 
            method='POST', 
            formdata={
                "sCnpj" : "", 
                "sRazaoSocial" : "", 
                "sEstado" : self.uf, 
                "sMunicipio" : "0", 
                "sBandeira" : "0", 
                "sProduto" : "0", 
                "sTipodePosto" : self.mapeamento_tipo_posto.get(self.fstation_type, 0), 
                "p" : "",
                "hPesquisar" : "PESQUISAR"},
            callback=self.parse_form,
            dont_filter=True,
            cb_kwargs={'p' : ""}
            )

    def parse_form(self, response, p: str):
        codigos_instalacoes = response.xpath("//input[contains(@onclick, 'jogaform')]/@onclick").re("\d+")
        if codigos_instalacoes:
            for codInst in codigos_instalacoes:
                yield FormRequest(
                    "https://postos.anp.gov.br/resultado.asp", 
                    method='POST', 
                    formdata={
                        "Cod_Inst" : codInst, 
                        "estado" : self.uf, 
                        "municipio": "0"
                    }, 
                    dont_filter=True,
                    callback=self.parse_posto_details,
                    cb_kwargs={"cod_inst" : codInst, "pag" : p}
                    )
        #check pagination
        pagination_form = response.xpath("//form[@name='formNext']").get()
        if pagination_form:
            #pag = response.xpath("//input[contains(@onclick,'value')]/@onclick").re(r'\d+')
            pag = response.xpath("//form[@name='formNext']//following-sibling::input/@onclick").re(r'\d+')[0]
            headers = {
                "Connection": "keep-alive",
                "Cache-Control": "max-age=0",
                "sec-ch-ua": "\" Not A;Brand\";v=\"99\", \"Chromium\";v=\"90\", \"Google Chrome\";v=\"90\"",
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
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
            } 
            yield FormRequest(
                url='https://postos.anp.gov.br/consulta.asp', 
                method='POST', 
                headers=headers,
                formdata={
                    "sCnpj" : "", 
                    "sRazaoSocial" : "", 
                    "sEstado" : self.uf, 
                    "sMunicipio" : "0", 
                    "sBandeira" : "0", 
                    "sProduto" : "0", 
                    "sTipodePosto" : self.mapeamento_tipo_posto.get(self.fstation_type, 0), 
                    "p" : pag,
                    "hPesquisar" : "PESQUISAR"},
                callback=self.parse_form,
                dont_filter=True,
                cb_kwargs={'p' : pag}
                )          
        else:
            if not p:
                self.logger.info("There aren't results to collect.")
            else:
                self.logger.info("There are no more pages to visit.")

    
    def parse_posto_details(self, response, cod_inst, pag: str):
        if pag == "":
            pag = 1
        self.logger.info(f"[{self.uf}][Page nº {pag}] Collecting data from fuel station with installation code number {cod_inst}.")
        containerEquipamentos = []
        dados_posto = PostoDetails()
        for el in response.xpath("//table"):
            width = el.attrib.get("width", None)
            if width == '760':
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
                                        status_posto = self.text_cleaning(fontline.get())
                                        dados_posto['status_posto'] = status_posto
                                which_feature = line.attrib.get("align")
                                if which_feature == 'right':
                                    for header in line.css("b"):
                                        header_text = self.text_cleaning(header.get())
                                        get_feature = self.mapeamento_features.get(header_text, None)
                                elif which_feature == 'left':
                                    for value in line.css("font"):
                                        value_text = self.text_cleaning(value.get())
                                        if get_feature:
                                            if get_feature == "municipio_uf":
                                                municipio, uf = value_text.split("/")
                                                dados_posto['municipio'] = self.text_cleaning(municipio)
                                                dados_posto['uf'] = self.text_cleaning(uf)
                                            elif get_feature == "bandeira_inicio":
                                                try:
                                                    bandeira, bandeira_inicio = value_text.split("/")
                                                except ValueError:
                                                    bandeira, bandeira_inicio = value_text.split("-")
                                                finally:
                                                    dados_posto['bandeira'] = self.text_cleaning(bandeira)
                                                    dados_posto['bandeira_inicio'] = parse(self.text_cleaning(bandeira_inicio), languages=['pt']).date().isoformat()
                                            else:
                                                if get_feature == 'data_publicacao':
                                                    dados_posto[get_feature] = parse(self.text_cleaning(value_text), languages=['pt']).date().isoformat()
                                                else:
                                                    dados_posto[get_feature] = self.text_cleaning(value_text)
                        if width_table == "644":
                            equipamento = {}
                            for line in elem.css("tr td"):
                                which_feature = line.attrib.get("width")
                                if which_feature == '450':
                                    for value in line.css("font"):
                                        value_text = self.text_cleaning(value.get())
                                        if value_text != "Produtos:" and value_text != "Tancagem (m³):" and value_text != "Bicos:":
                                            equipamento['produto'] = value_text
                                elif which_feature == '103':
                                    for value in line.css("font"):
                                        value_text = self.text_cleaning(value.get())
                                        if value_text != "Produtos:" and value_text != "Tancagem (m³):" and value_text != "Bicos:":
                                            equipamento['tancagem'] = float(value_text.replace(",","."))                                  
                                elif which_feature == '92':
                                    for value in line.css("font"):
                                        value_text = self.text_cleaning(value.get())
                                        if value_text != "Produtos:" and value_text != "Tancagem (m³):" and value_text != "Bicos:":
                                            equipamento['bicos'] = float(value_text.replace(",","."))
                                if equipamento.get("produto", "") != "" and equipamento.get("tancagem", "") != "" and equipamento.get("bicos","") != "":
                                    containerEquipamentos.append(equipamento)
                                    equipamento = {}   
        
        dados_posto['equipamentos'] = containerEquipamentos       
        dados_posto['datetime_collected'] = datetime.datetime.utcnow().isoformat()
        yield dados_posto