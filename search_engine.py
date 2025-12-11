import os
import requests
import wikipediaapi
import logging
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class SearchEngine:
    def __init__(self):
        """Инициализация поискового движка"""
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.google_cse_id = os.getenv('GOOGLE_CSE_ID')
        
        # Проверка ключей
        if not self.google_api_key or not self.google_cse_id:
            logger.warning("Google API ключи не настроены. Поиск будет ограничен.")
        
        # Wikipedia
        self.wiki_wiki = wikipediaapi.Wikipedia(
            language='ru',
            extract_format=wikipediaapi.ExtractFormat.WIKI,
            user_agent='KonspektBot/1.0'
        )
        
        # Сессия для запросов
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.session.timeout = 15
    
    def search_google(self, query, num_results=3):
        """Поиск через Google Custom Search API"""
        if not self.google_api_key or not self.google_cse_id:
            logger.error("Google API не настроен")
            return []
        
        try:
            # Кодируем запрос
            encoded_query = quote_plus(query)
            
            # Формируем URL
            url = (
                f"https://www.googleapis.com/customsearch/v1?"
                f"key={self.google_api_key}&"
                f"cx={self.google_cse_id}&"
                f"q={encoded_query}&"
                f"num={num_results}&"
                f"lr=lang_ru&"
                f"gl=ru"
            )
            
            logger.info(f"Запрос к Google: {query}")
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            if 'items' in data:
                for item in data['items']:
                    results.append({
                        'source': 'Google',
                        'title': item.get('title', 'Без названия'),
                        'url': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                        'content': self._clean_content(item.get('snippet', ''))
                    })
            
            logger.info(f"Google нашел: {len(results)} результатов")
            return results
            
        except requests.exceptions.Timeout:
            logger.error("Таймаут запроса к Google")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка сети Google: {e}")
            return []
        except Exception as e:
            logger.error(f"Ошибка Google API: {e}")
            return []
    
    def search_wikipedia(self, query):
        """Поиск в Wikipedia"""
        try:
            # Прямой поиск
            page = self.wiki_wiki.page(query)
            
            if page.exists():
                return {
                    'source': 'Wikipedia',
                    'title': page.title,
                    'summary': page.summary[:1000],
                    'url': page.fullurl,
                    'content': self._clean_content(page.summary[:1500])
                }
            
            # Поиск по схожим запросам
            search_results = self.wiki_wiki.search(query)
            if search_results:
                first_result = self.wiki_wiki.page(search_results[0])
                if first_result.exists():
                    return {
                        'source': 'Wikipedia',
                        'title': first_result.title,
                        'summary': first_result.summary[:1000],
                        'url': first_result.fullurl,
                        'content': self._clean_content(first_result.summary[:1500])
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка Wikipedia: {e}")
            return None
    
    def search_all_sources(self, query, max_results=3):
        """Поиск по всем источникам"""
        all_results = []
        
        # 1. Wikipedia (всегда первый)
        wiki_result = self.search_wikipedia(query)
        if wiki_result:
            all_results.append(wiki_result)
            logger.info(f"Wikipedia: {wiki_result['title']}")
        
        # 2. Google (если есть ключи)
        if self.google_api_key and self.google_cse_id:
            google_results = self.search_google(query, num_results=max_results)
            for result in google_results:
                if len(all_results) >= max_results + 1:  # +1 для Wikipedia
                    break
                all_results.append(result)
        
        # 3. Если ничего не найдено
        if not all_results:
            logger.warning(f"Не найдено результатов для: {query}")
        
        return all_results
    
    def _clean_content(self, text):
        """Очистка текста"""
        if not text:
            return ""
        
        # Удаляем лишние пробелы
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        cleaned = ' '.join(lines)
        
        # Ограничиваем длину
        return cleaned[:3000]

# Для совместимости со старым кодом
search_engine = SearchEngine()
