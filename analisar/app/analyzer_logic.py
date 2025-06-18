# app/analyzer_logic.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class WebsiteAnalyzer:
    def __init__(self, url):
        self.url = self._normalize_url(url)
        self.domain = urlparse(self.url).netloc
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AnalisadorPROBot/1.0 (+https://analisadorpro.com)' # Custom User-Agent
        })
        self.collected_links = set() # Para evitar loops infinitos em sitemap (se fosse usado)

    def _normalize_url(self, url):
        if not url.startswith(('http://', 'https://')):
            return 'https://' + url
        return url

    def analyze(self):
        results = {}
        try:
            print(f"Iniciando análise para: {self.url}")
            response = self.session.get(self.url, timeout=10)
            response.raise_for_status() # Lança exceção para status codes de erro (4xx, 5xx)
            soup = BeautifulSoup(response.text, 'html.parser')

            # SEO Check (EXISTENTE)
            results['seo_check'] = self._perform_seo_check(soup)

            # NOVAS VERIFICAÇÕES DE SEO ON-PAGE
            results['onpage_seo_check'] = self._perform_onpage_seo_checks(soup)

            # Link Check (EXISTENTE)
            results['link_check'] = self._perform_link_check(soup, self.url)

            print(f"Análise concluída para: {self.url}")
        except requests.exceptions.Timeout:
            results['error'] = 'Tempo limite excedido ao conectar ao site.'
            print(f"Erro de timeout para: {self.url}")
        except requests.exceptions.RequestException as e:
            results['error'] = f'Erro de conexão ou HTTP: {e}'
            print(f"Erro de conexão para {self.url}: {e}")
        except Exception as e:
            results['error'] = f'Ocorreu um erro inesperado: {e}'
            print(f"Erro inesperado para {self.url}: {e}")

        return results

    def _perform_seo_check(self, soup):
        seo_results = {}
        # Título
        title_tag = soup.find('title')
        title_text = title_tag.get_text(strip=True) if title_tag else 'N/A'
        seo_results['title'] = {'text': title_text, 'length': len(title_text)}

        # Meta Description
        meta_description_tag = soup.find('meta', attrs={'name': 'description'})
        meta_description_text = meta_description_tag['content'].strip() if meta_description_tag and 'content' in meta_description_tag.attrs else 'N/A'
        seo_results['meta_description'] = {'text': meta_description_text, 'length': len(meta_description_text)}

        return seo_results

    # NOVO MÉTODO PARA VERIFICAÇÕES DE SEO ON-PAGE
    def _perform_onpage_seo_checks(self, soup):
        onpage_results = {
            'h_tags': {'h1': [], 'h2': [], 'h3': [], 'h4': [], 'h5': [], 'h6': []},
            'img_alt_tags': {'missing': [], 'empty': [], 'present': []},
            'robots_meta': {'present': False, 'content': 'N/A'},
            'canonical_tag': {'present': False, 'href': 'N/A', 'is_valid': False}
        }

        # Verificação de Tags de Cabeçalho (H1, H2, H3, etc.)
        for i in range(1, 7): # H1 até H6
            h_tags = soup.find_all(f'h{i}')
            for tag in h_tags:
                onpage_results['h_tags'][f'h{i}'].append(tag.get_text(strip=True))

        # Verificação de Atributos Alt em Imagens
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

        # Verificação de Robots Meta Tag
        robots_meta = soup.find('meta', attrs={'name': 'robots'})
        if robots_meta and 'content' in robots_meta.attrs:
            onpage_results['robots_meta']['present'] = True
            onpage_results['robots_meta']['content'] = robots_meta['content'].strip()

        # Verificação de Canonical Tag
        canonical_link = soup.find('link', rel='canonical', href=True)
        if canonical_link and 'href' in canonical_link.attrs:
            onpage_results['canonical_tag']['present'] = True
            onpage_results['canonical_tag']['href'] = canonical_link['href'].strip()
            # Uma validação básica: se a canonical href é uma URL válida
            if canonical_link['href'].strip().startswith(('http://', 'https://')):
                onpage_results['canonical_tag']['is_valid'] = True

        return onpage_results


    def _perform_link_check(self, soup, base_url):
        broken_links = []
        links = soup.find_all('a', href=True)
        for link_tag in links:
            href = link_tag['href']
            full_url = urljoin(base_url, href) # Converte links relativos para absolutos

            # Ignora fragmentos e links de e-mail/âncora interna
            if full_url.startswith('mailto:') or '#' in full_url.split('/')[-1].split('?')[0]:
                continue

            try:
                # Usamos HEAD request para verificar status sem baixar o conteúdo completo
                # No entanto, alguns sites podem bloquear HEAD ou retornar 403, então GET é mais confiável para status
                link_response = self.session.get(full_url, timeout=5, stream=True) # Use stream=True para não baixar tudo
                status_code = link_response.status_code
                link_response.close() # Fechar a conexão imediatamente

                if status_code >= 400:
                    broken_links.append({'url': full_url, 'status_code': status_code})
            except requests.exceptions.RequestException as e:
                broken_links.append({'url': full_url, 'status_code': f'Erro: {e}'})
            except Exception as e:
                broken_links.append({'url': full_url, 'status_code': f'Erro inesperado: {e}'})

        return {'broken_links': broken_links}