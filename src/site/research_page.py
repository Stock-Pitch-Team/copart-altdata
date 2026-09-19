"""Research lab page: explicit evidence status for each thesis test."""
import json
import pandas as pd
from src.common import PROCESSED, read_meta

def page_research():
    tables=[]
    for name,title in [('research_carriers','3. Carrier exposure: measured public data'),('research_allocation','Carrier allocation: what growth can and cannot offset'),('research_supply','5. Long-term supply: claims frequency can overwhelm TLF'),('research_earnings','6. Earnings: translate operating assumptions into EPS')]:
        d=pd.read_csv(PROCESSED/f'{name}.csv').drop(columns=['source_url'],errors='ignore')
        rows=[[round(x,3) if isinstance(x,float) else x for x in row] for row in d.itertuples(index=False,name=None)]
        tables.append({'title':title,'columns':[c.replace('_',' ') for c in d.columns],'rows':rows,'meta':read_meta(name)})
    results=json.loads((PROCESSED/'research_import_results.json').read_text(encoding='utf-8'))
    return {'template':'research.html','page_title':'Research lab','heading':'Six ways to test the thesis','eyebrow':'Evidence, not confirmation bias','lede':'Public carrier comparisons and operating scenarios are ready. Recovery, inventory and yard coverage engines are implemented; their measured conclusions await source datasets. A weaker result is useful evidence too.','page_description':'Reproducible Copart versus IAA research, public carrier analysis, import workflows and interactive operating sensitivities.','tables':tables,'results':results}
