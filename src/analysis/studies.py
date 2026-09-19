"""Pure research calculations. Outputs are observational, not causal estimates."""
import numpy as np
import pandas as pd

def matched_recovery(d):
    if d.empty: return {'pairs':0}
    d=d.copy()
    d['week']=pd.to_datetime(d.sale_date).dt.to_period('W').astype(str)
    exact=['year','make','model','damage','title','region','week']
    for c in exact: d[c]=d[c].astype(str).str.strip().str.lower()
    d['net']=d.sale_price-d.seller_fees-d.transport-d.storage
    left=d[d.platform=='Copart'].sort_values('lot_id')
    right=d[d.platform=='IAA'].sort_values('lot_id')
    used=set(); pairs=[]
    for _,a in left.iterrows():
        candidates=right[~right.lot_id.isin(used)]
        for c in exact: candidates=candidates[candidates[c]==a[c]]
        candidates=candidates[(candidates.mileage-a.mileage).abs()<=10000]
        if candidates.empty: continue
        b=candidates.loc[(candidates.mileage-a.mileage).abs().idxmin()]
        used.add(b.lot_id); pairs.append((a.net-b.net,a.mileage-b.mileage))
    if not pairs: return {'pairs':0,'eligible_sales':len(d)}
    x=np.array(pairs); rng=np.random.default_rng(42)
    lo,hi=(None,None) if len(x)<10 else tuple(np.percentile([rng.choice(x[:,0],len(x),replace=True).mean() for _ in range(2000)],[2.5,97.5]))
    return {'pairs':len(x),'eligible_sales':len(d),'matched_fraction':2*len(x)/len(d), 'net_advantage_usd':float(x[:,0].mean()),'ci_low':lo,'ci_high':hi,'mean_mileage_gap':float(x[:,1].mean()),'mean_absolute_mileage_gap':float(abs(x[:,1]).mean())}

def inventory_summary(d, manifests):
    if d.empty: return []
    if manifests.empty: raise ValueError('Inventory requires dated completeness manifests')
    d=d.merge(manifests[['platform','date','complete']],on=['platform','date'],how='left',validate='many_to_one')
    if d.complete.isna().any(): raise ValueError('Every snapshot requires a manifest')
    out=[]
    for platform,g in d.groupby('platform'):
        complete=manifests[(manifests.platform==platform)&(manifests.complete==1)]
        dates=sorted(complete.date.unique())
        if not dates: continue
        eligible=g[g.complete==1]; sold=0; durations=[]; censored=0; relisted=0
        for _,lot in eligible.groupby('lot_id'):
            lot=lot.sort_values('date')
            active=lot[lot.status=='active']
            sales=lot[lot.status=='sold']
            if not sales.empty and not active.empty and sales.date.iloc[0]>=active.date.iloc[0]:
                sold+=1; durations.append((pd.Timestamp(sales.date.iloc[0])-pd.Timestamp(active.date.iloc[0])).days)
            else: censored+=1
            positions=[dates.index(x) for x in active.date]
            relisted+=int(any(b-a>1 for a,b in zip(positions,positions[1:])))
        n=eligible.lot_id.nunique()
        out.append({'platform':platform,'observed_lots':n,'confirmed_sales':sold,'unresolved_or_withdrawn':censored,'confirmed_sale_fraction':sold/n if n else None,'median_observed_days_sold_only':float(np.median(durations)) if durations else None,'reappearances':relisted,'complete_days':len(dates),'incomplete_days':int(((manifests.platform==platform)&(manifests.complete==0)).sum())})
    return out

def coverage(yards, storms):
    if yards.empty or storms.empty: return []
    out=[]
    for platform,g in yards.groupby('platform'):
        a=np.radians(storms[['latitude','longitude']].to_numpy(float)); b=np.radians(g[['latitude','longitude']].to_numpy(float))
        nearest=np.full(len(a),np.inf)
        for point in b:
            h=np.sin((a[:,0]-point[0])/2)**2+np.cos(a[:,0])*np.cos(point[0])*np.sin((a[:,1]-point[1])/2)**2
            nearest=np.minimum(nearest,3958.7613*2*np.arcsin(np.sqrt(np.clip(h,0,1))))
        for radius in [50,100,150]:
            out.append({'platform':platform,'radius_miles':radius,'yards':len(g),'events':len(a),'covered_events':int((nearest<=radius).sum()),'covered_pct':float(100*(nearest<=radius).mean())})
    return out

def supply_index(exposure_growth, claim_growth, tlf_start, tlf_end, years=5):
    if not 0<tlf_start<=1 or not 0<tlf_end<=1 or exposure_growth<=-1 or claim_growth<=-1 or years<0: raise ValueError('Invalid supply assumptions')
    return 100*(1+exposure_growth)**years*(1+claim_growth)**years*tlf_end/tlf_start

# FY2026 consolidated reported values, USD millions. SEC 10 September 2026.
BASE={'service':3969.520,'vehicle':696.689,'facility':1755.747,'vehicle_cost':616.463,'other_cost':641.409,'interest':181.923,'other_income':.464,'nci_loss':3.873,'tax_rate':354.580/1834.977,'shares':956.860}

def earnings(volume=0,rpu=0,inflation=0,variable_share=.6,interest_delta=0,share_change=0):
    if min(volume,rpu,inflation,share_change)<=-1 or not 0<=variable_share<=1: raise ValueError('Invalid earnings assumptions')
    b=BASE
    revenue=b['service']*(1+volume)*(1+rpu)+b['vehicle']*(1+volume)
    facility=b['facility']*((1-variable_share)+variable_share*(1+volume))*(1+inflation)
    costs=facility+b['vehicle_cost']*(1+volume)+b['other_cost']*(1+inflation)
    operating=revenue-costs
    eps=((operating+b['interest']+interest_delta+b['other_income'])*(1-b['tax_rate'])+b['nci_loss'])/(b['shares']*(1+share_change))
    return {'revenue_m':revenue,'operating_income_m':operating,'operating_margin_pct':100*operating/revenue,'eps':eps}
