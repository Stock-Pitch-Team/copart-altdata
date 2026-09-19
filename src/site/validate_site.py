"""Validate local links and strict JSON embedded in generated pages."""
import json
from pathlib import Path
from urllib.parse import urlsplit, unquote
from bs4 import BeautifulSoup
from src.common import DOCS

def validate():
    count=0
    for path in DOCS.glob('*.html'):
        html=path.read_text(encoding='utf-8'); soup=BeautifulSoup(html,'html.parser')
        assert soup.title and soup.find('h1'), f'Missing page title: {path}'
        for script in soup.select('script[type="application/json"]'):
            json.loads(script.string or script.get_text(),parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
            count+=1
        for element in soup.select('[href], [src]'):
            url=element.get('href') or element.get('src'); parsed=urlsplit(url)
            if parsed.scheme or parsed.netloc: continue
            target=(path.parent/unquote(parsed.path)) if parsed.path else path
            assert target.exists(), f'Broken link {path.name}: {url}'
            if parsed.fragment and target.suffix=='.html':
                dest=soup if target==path else BeautifulSoup(target.read_text(encoding='utf-8'),'html.parser')
                assert dest.find(id=unquote(parsed.fragment)), f'Missing anchor {url}'
    assert (DOCS/'research.html').exists()
    print(f'Validated local links and {count} JSON blocks across {len(list(DOCS.glob("*.html")))} pages.')
if __name__=='__main__': validate()
