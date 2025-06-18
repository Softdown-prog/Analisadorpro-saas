# app/analysis/crawler.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from datetime import datetime # Importar para data do sitemap

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WebsiteAnalyzer:
    def __init__(self, url, user_plan=None):
        self.url = self._normalize_url(url)
        self.domain = urlparse(self.url).netloc
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AnalisadorPROBot/1.0 (+https://analisadorpro.com)' # Custom User-Agent
        })
        self.collected_links = set()
        self.user_plan = user_plan # Armazena o objeto do plano do usuário

    def _normalize_url(self, url):
        if not url.startswith(('http://', 'https://')):
            return 'https://' + url
        return url

    def analyze(self):
        results = {}
        try:
            logging.info(f"Iniciando análise para: {self.url} (Plano: {self.user_plan.nome if self.user_plan else 'N/A'})")
            response = self.session.get(self.url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            results['seo_check'] = self._perform_seo_check(soup)

            if self.user_plan and self.user_plan.permite_seguranca_seo_avancado:
                logging.info(f"Executando análise de SEO On-Page avançada para o plano: {self.user_plan.nome}")
                results['onpage_seo_check'] = self._perform_onpage_seo_checks(soup)
            else:
                logging.info(f"Análise de SEO On-Page avançada e segurança restrita para o plano: {self.user_plan.nome if self.user_plan else 'N/A'}")
                results['onpage_seo_check'] = {'message': 'Recurso avançado. Faça login e assine um plano Premium para acesso total.'}

            results['link_check'] = self._perform_link_check(soup, self.url)

            logging.info(f"Análise concluída para: {self.url}")
        except requests.exceptions.Timeout:
            results['error'] = 'Tempo limite excedido ao conectar ao site.'
            logging.error(f"Erro de timeout para: {self.url}")
        except requests.exceptions.RequestException as e:
            results['error'] = f'Erro de conexão ou HTTP: {e}'
            logging.error(f"Erro de conexão para {self.url}: {e}")
        except Exception as e:
            results['error'] = f'Ocorreu um erro inesperado: {e}'
            logging.error(f"Erro inesperado para {self.url}: {e}", exc_info=True)

        return results

    def _perform_seo_check(self, soup):
        seo_results = {}
        title_tag = soup.find('title')
        title_text = title_tag.get_text(strip=True) if title_tag else 'N/A'
        seo_results['title'] = {'text': title_text, 'length': len(title_text)}
        meta_description_tag = soup.find('meta', attrs={'name': 'description'})
        meta_description_text = meta_description_tag['content'].strip() if meta_description_tag and 'content' in meta_description_tag.attrs else 'N/A'
        seo_results['meta_description'] = {'text': meta_description_text, 'length': len(meta_description_text)}
        return seo_results

    def _perform_onpage_seo_checks(self, soup):
        onpage_results = {
            'h_tags': {'h1': [], 'h2': [], 'h3': [], 'h4': [], 'h5': [], 'h6': []},
            'img_alt_tags': {'missing': [], 'empty': [], 'present': []},
            'robots_meta': {'present': False, 'content': 'N/A'},
            'canonical_tag': {'present': False, 'href': 'N/A', 'is_valid': False}
        }

        for i in range(1, 7):
            h_tags = soup.find_all(f'h{i}')
            for tag in h_tags:
                onpage_results['h_tags'][f'h{i}'].append(tag.get_text(strip=True))

        images = soup.find_all('img')
        for img in images:
            src = img.get('src', 'N/A')
            alt = img.get('alt')
            if alt is None:
                onpage_results['img_alt_tags']['missing'].append(src)
            elif alt.strip() == '':
                onpage_results['img_alt_tags']['empty'].append(src)
            else:
                onpage_results['img_alt_tags']['present'].append(src)

        robots_meta = soup.find('meta', attrs={'name': 'robots'})
        if robots_meta and 'content' in robots_meta.attrs:
            onpage_results['robots_meta']['present'] = True
            onpage_results['robots_meta']['content'] = robots_meta['content'].strip()

        canonical_link = soup.find('link', rel='canonical', href=True)
        if canonical_link and 'href' in canonical_link.attrs:
            onpage_results['canonical_tag']['present'] = True
            onpage_results['canonical_tag']['href'] = canonical_link['href'].strip()
            if canonical_link['href'].strip().startswith(('http://', 'https://')):
                onpage_results['canonical_tag']['is_valid'] = True

        return onpage_results

    def _perform_link_check(self, soup, base_url):
        broken_links = []
        links = soup.find_all('a', href=True)
        for link_tag in links:
            href = link_tag['href']
            full_url = urljoin(base_url, href)

            if full_url.startswith('mailto:') or '#' in full_url.split('/')[-1].split('?')[0]:
                continue

            try:
                link_response = self.session.get(full_url, timeout=5, stream=True)
                status_code = link_response.status_code
                link_response.close()

                if status_code >= 400:
                    broken_links.append({'url': full_url, 'status_code': status_code})
            except requests.exceptions.RequestException as e:
                broken_links.append({'url': full_url, 'status_code': f'Erro: {e}'})
            except Exception as e:
                broken_links.append({'url': full_url, 'status_code': f'Erro inesperado: {e}'})

        return {'broken_links': broken_links}

    def generate_sitemap_xml(self): # NOVO: Método para gerar Sitemap XML
        # Para uma geração básica, vamos rastrear a página inicial e coletar links internos
        # Para um sitemap completo, seria necessário um crawler mais profundo (fora do escopo deste método simples)
        sitemap_urls = set()
        sitemap_urls.add(self.url) # Adiciona a URL base

        try:
            response = self.session.get(self.url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for link_tag in soup.find_all('a', href=True):
                href = link_tag['href']
                full_url = urljoin(self.url, href)
                # Adiciona apenas links que pertencem ao mesmo domínio
                if urlparse(full_url).netloc == self.domain:
                    sitemap_urls.add(full_url)
        except Exception as e:
            logging.error(f"Erro ao coletar links para sitemap de {self.url}: {e}", exc_info=True)
            # Continua mesmo com erro, gerando sitemap com o que foi coletado

        # Cria o XML do sitemap
        sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        lastmod_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00") # Formato W3C Datetime
        
        for url in sorted(list(sitemap_urls)):
            sitemap_xml += '  <url>\n'
            sitemap_xml += f'    <loc>{url}</loc>\n'
            sitemap_xml += f'    <lastmod>{lastmod_date}</lastmod>\n'
            sitemap_xml += '  </url>\n'
        
        sitemap_xml += '</urlset>'
        
        return sitemap_xml