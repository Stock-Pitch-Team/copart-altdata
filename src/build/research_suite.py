"""Build six research workstreams; publish only aggregate imported results."""
import json
import pandas as pd
from src.common import ROOT, PROCESSED, write_dataset
from src.analysis.imports import load, SCHEMAS
from src.analysis.studies import matched_recovery, inventory_summary, coverage, supply_index, earnings, BASE

SOURCE='https://www.sec.gov/Archives/edgar/data/900075/000119312526387902/cprt-ex99_1.htm'

def build(public_only=False):
    for kind,columns in SCHEMAS.items():
        (ROOT/'data'/'templates'/f'{kind}.csv').write_text(columns+'\n',encoding='utf-8')
    carriers=pd.read_csv(ROOT/'data'/'manual'/'carrier_auto_exposure.csv')
    carriers['policy_growth_pct']=100*(carriers.auto_policies_thousands/carriers.prior_year_thousands-1)
    write_dataset(carriers,'research_carriers',source='; '.join(carriers.source_url.unique()),method='Personal auto policies: Progressive agency plus direct; Allstate Protection auto. Compare June with June. August is an update, not a synchronized comparison.',gaps='Two carriers only; policies are not claims or salvage units. Different products and territories; allocation to auctioneers is unknown.',units='Thousands of policies; percent',frequency='Monthly/quarterly')
    allocation=[]
    # Illustrative normalized book, not estimates of actual carrier allocation.
    for weight in [.1,.25,.4]:
        for retained in [.5,.75,1]:
            p=carriers[(carriers.carrier=='Progressive')&(carriers.period=='2026-06-30')].iloc[0].policy_growth_pct/100
            other=carriers[carriers.carrier=='Allstate Protection'].iloc[0].policy_growth_pct/100
            value=100*(weight*(1+p)*retained+(1-weight)*(1+other))
            allocation.append({'progressive_starting_weight_pct':weight*100,'progressive_allocation_retained_pct':retained*100,'other_book_growth_proxy_pct':other*100,'volume_index':value})
    write_dataset(pd.DataFrame(allocation),'research_allocation',source='Public carrier exposure dataset; analyst scenarios',method='100 × [starting Progressive weight × policy growth factor × retained allocation + remaining weight × Allstate policy growth factor]. Claims and TLF held flat.',gaps='Weights and retained allocation are hypothetical; Allstate is only a proxy for the remaining book. Not an estimate of actual Copart volume.',units='Starting volume = 100',frequency='Scenario')
    supply=[]
    for claims in [-.05,-.025,0]:
        for end in [.22,.25,.28]:
            supply.append({'exposure_growth_pct':1,'annual_claim_frequency_change_pct':claims*100,'starting_tlf_pct':22,'ending_tlf_pct':end*100,'years':5,'volume_index':supply_index(.01,claims,.22,end),'break_even_ending_tlf_pct':22/((1.01*(1+claims))**5)})
    write_dataset(pd.DataFrame(supply),'research_supply',source='Analyst sensitivity assumptions; not observed projections',method='Exposure × claim frequency × total-loss frequency. Five years of compounded exposure and claims, endpoint TLF ratio. Base volume = 100.',gaps='22% starting TLF is a round scenario anchor, not a new measurement. Excludes market share, catastrophic spikes and non-insurance units. No probabilities assigned.',units='Percent; normalized units',frequency='Scenario')
    bridge=[]
    for name,v,r,c,f,i,s in [('Reported baseline',0,0,0,.6,0,0),('Pressure',-.05,0,.04,.6,-50,0),('Recovery',.03,.02,.025,.6,0,-.01),('Expansion',.07,.03,.025,.6,0,-.01)]:
        bridge.append(dict(scenario=name,volume_growth_pct=v*100,service_rpu_growth_pct=r*100,cost_inflation_pct=c*100,facility_variable_share_pct=f*100,interest_delta_m=i,share_change_pct=s*100,**earnings(v,r,c,f,i,s)))
    write_dataset(pd.DataFrame(bridge),'research_earnings',source=SOURCE,method='FY2026 consolidated revenue and costs. Service revenue scales by volume and RPU; vehicle revenue/cost scale by volume. Facility costs split fixed/variable with assumed 60% variable; other operating costs inflate. Reported tax rate and NCI adjustment; diluted shares adjusted by scenario.',gaps='Fixed/variable split is assumed, not disclosed. Cost inflation bundles fuel and wages. No acquisition contributions, purchase accounting, capex, working capital or full cash-flow forecast. Scenarios are not price targets.',units='USD millions; EPS USD',frequency='Annual scenario')
    result_path=PROCESSED/'research_import_results.json'
    if public_only:
        if not result_path.exists():
            raise ValueError('Public-only refresh requires existing aggregate import results')
        payload=json.loads(result_path.read_text(encoding='utf-8'))
        payload.update(earnings_baseline=BASE,source=SOURCE)
    else:
        recovery=matched_recovery(load('sales'))
        inventory=inventory_summary(load('inventory'),load('manifests'))
        yard=coverage(load('yards'),load('storms'))
        payload={'recovery':recovery,'inventory':inventory,'coverage':yard,'earnings_baseline':BASE,'source':SOURCE}
    PROCESSED.mkdir(parents=True,exist_ok=True)
    (PROCESSED/'research_import_results.json').write_text(json.dumps(payload,indent=2,allow_nan=False),encoding='utf-8')
    print('Built public carrier analysis, allocation/supply/earnings scenarios and aggregate import studies.')
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--public-only',action='store_true',help='Refresh public scenarios while preserving published import aggregates')
    build(parser.parse_args().public_only)
