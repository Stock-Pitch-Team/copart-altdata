"""Validated, private research imports. No auction scraping or raw-data publishing."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from src.common import ROOT

SCHEMAS = {
 'sales': 'platform,lot_id,sale_date,year,make,model,mileage,damage,title,region,sale_price,seller_fees,transport,storage,source_url',
 'inventory': 'platform,lot_id,date,status,source_url',
 'manifests': 'platform,date,complete,source_url',
 'yards': 'platform,yard_id,latitude,longitude,acres,ownership,source_url',
 'storms': 'event_id,latitude,longitude,source_url',
}
KEYS = {'sales':['platform','lot_id'], 'inventory':['platform','lot_id','date'], 'manifests':['platform','date'], 'yards':['platform','yard_id'], 'storms':['event_id']}

def validate(kind, frame):
    columns = SCHEMAS[kind].split(',')
    if set(frame.columns) != set(columns):
        raise ValueError(f'{kind}: columns must be exactly {columns}')
    d = frame[columns].copy()
    if d.empty:
        return d
    if d.isna().any().any() or d.astype(str).apply(lambda s:s.str.strip().eq('')).any().any():
        raise ValueError('Missing fields are not permitted; unknown fees must not be entered as zero')
    if d.duplicated(KEYS[kind]).any():
        raise ValueError('Duplicate identifiers')
    if 'platform' in d and not d.platform.isin(['Copart','IAA']).all():
        raise ValueError('platform must be Copart or IAA')
    if not d.source_url.str.match(r'https?://\S+$').all():
        raise ValueError('A public source or authorized provider URL is required')
    for c in ['date','sale_date']:
        if c in d:
            d[c] = pd.to_datetime(d[c], format='%Y-%m-%d', errors='raise').dt.strftime('%Y-%m-%d')
    for c in ['year','mileage','sale_price','seller_fees','transport','storage','latitude','longitude','acres']:
        if c in d:
            d[c] = pd.to_numeric(d[c], errors='raise')
            if not np.isfinite(d[c]).all(): raise ValueError(f'{c} must be finite')
            if c not in ['latitude','longitude'] and (d[c]<0).any(): raise ValueError(f'{c} cannot be negative')
    if 'year' in d and ((d.year%1!=0)|(d.year<1900)|(d.year>2100)).any(): raise ValueError('Invalid model year')
    if 'latitude' in d and ((d.latitude.abs()>90)|(d.longitude.abs()>180)).any(): raise ValueError('Invalid coordinates')
    if kind == 'inventory' and not d.status.isin(['active','sold','withdrawn']).all(): raise ValueError('Invalid status')
    if kind == 'manifests':
        if not d.complete.astype(str).isin(['0','1']).all(): raise ValueError('complete must be 0 or 1')
        d.complete = d.complete.astype(int)
    if kind == 'yards' and not d.ownership.isin(['owned','leased','unknown']).all(): raise ValueError('Invalid ownership')
    return d

def load(kind):
    path = ROOT/'data'/'private'/f'{kind}.csv'
    return validate(kind, pd.read_csv(path, dtype=str)) if path.exists() else pd.DataFrame(columns=SCHEMAS[kind].split(','))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind',choices=SCHEMAS)
    parser.add_argument('path',type=Path)
    args=parser.parse_args()
    d=validate(args.kind,pd.read_csv(args.path,dtype=str))
    if d.empty: raise ValueError('Template is empty; nothing imported')
    dest=ROOT/'data'/'private'/f'{args.kind}.csv'
    dest.parent.mkdir(parents=True,exist_ok=True)
    d.to_csv(dest,index=False)
    print(f'Validated {len(d)} rows. Replaced private {args.kind} input; rebuild to publish aggregate results.')
if __name__=='__main__': main()
