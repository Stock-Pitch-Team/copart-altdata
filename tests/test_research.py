import unittest
import pandas as pd
from src.analysis.imports import validate, SCHEMAS
from src.analysis.studies import matched_recovery, inventory_summary, coverage, supply_index, earnings

class ResearchTests(unittest.TestCase):
    def sale(self,platform,lot,mileage=50000,price=5000):
        return dict(platform=platform,lot_id=lot,sale_date='2026-06-01',year=2020,make='Ford',model='Focus',mileage=mileage,damage='front',title='salvage',region='TX',sale_price=price,seller_fees=100,transport=200,storage=50,source_url='https://example.org/authorized')
    def test_net_matching_and_no_reuse(self):
        d=pd.DataFrame([self.sale('Copart','a',price=6000),self.sale('Copart','b'),self.sale('IAA','c')])
        result=matched_recovery(validate('sales',d))
        self.assertEqual(result['pairs'],1);self.assertEqual(result['net_advantage_usd'],1000);self.assertIsNone(result['ci_low'])
    def test_costs_can_reverse_advantage(self):
        a=self.sale('Copart','a',price=6000);a['seller_fees']=1600
        result=matched_recovery(pd.DataFrame([a,self.sale('IAA','b')]))
        self.assertEqual(result['net_advantage_usd'],-500)
    def test_caliper_and_exact_match(self):
        a=self.sale('Copart','a');b=self.sale('IAA','b',mileage=60001)
        self.assertEqual(matched_recovery(pd.DataFrame([a,b]))['pairs'],0)
        b['mileage']=50000;b['title']='clean'
        self.assertEqual(matched_recovery(pd.DataFrame([a,b]))['pairs'],0)
    def test_bootstrap_known_difference(self):
        rows=[]
        for i in range(12): rows.extend([self.sale('Copart',str(i),price=5100),self.sale('IAA',str(i))])
        result=matched_recovery(pd.DataFrame(rows))
        self.assertEqual(result['ci_low'],100);self.assertEqual(result['ci_high'],100)
    def test_duplicate_rejected(self):
        row=self.sale('Copart','a')
        with self.assertRaises(ValueError):validate('sales',pd.DataFrame([row,row]))
    def test_missing_fees_rejected(self):
        row=self.sale('Copart','a');row['storage']=None
        with self.assertRaises(ValueError):validate('sales',pd.DataFrame([row]))
    def test_nonfinite_rejected(self):
        row=self.sale('Copart','a');row['sale_price']=float('inf')
        with self.assertRaises(ValueError):validate('sales',pd.DataFrame([row]))
    def test_extra_private_field_rejected(self):
        row=self.sale('Copart','a');row['vin']='private'
        with self.assertRaises(ValueError):validate('sales',pd.DataFrame([row]))
    def test_incomplete_day_is_not_sale_or_relisting(self):
        manifests=pd.DataFrame({'platform':['Copart']*3,'date':['2026-06-01','2026-06-02','2026-06-03'],'complete':[1,0,1]})
        inventory=pd.DataFrame({'platform':['Copart']*3,'lot_id':['a']*3,'date':manifests.date,'status':['active','sold','active']})
        result=inventory_summary(inventory,manifests)[0]
        self.assertEqual(result['confirmed_sales'],0);self.assertEqual(result['reappearances'],0);self.assertEqual(result['unresolved_or_withdrawn'],1)
    def test_confirmed_duration(self):
        manifests=pd.DataFrame({'platform':['IAA']*2,'date':['2026-06-01','2026-06-04'],'complete':[1,1]})
        d=pd.DataFrame({'platform':['IAA']*2,'lot_id':['a']*2,'date':manifests.date,'status':['active','sold']})
        self.assertEqual(inventory_summary(d,manifests)[0]['median_observed_days_sold_only'],3)
    def test_manifest_required(self):
        with self.assertRaises(ValueError):inventory_summary(pd.DataFrame({'platform':['Copart']}),pd.DataFrame())
    def test_overlap_does_not_double_count(self):
        yards=pd.DataFrame({'platform':['Copart','Copart'],'latitude':[30,30],'longitude':[-97,-97]})
        storms=pd.DataFrame({'latitude':[30,40],'longitude':[-97,-97]})
        for row in coverage(yards,storms):self.assertEqual(row['covered_events'],1);self.assertEqual(row['covered_pct'],50)
    def test_supply_offsets_and_break_even(self):
        self.assertEqual(supply_index(0,0,.22,.22),100)
        self.assertLess(supply_index(.01,-.05,.22,.25),100)
        end=.22/(1.01*.975)**5
        self.assertAlmostEqual(supply_index(.01,-.025,.22,end),100)
    def test_financial_reconciliation(self):
        b=earnings();self.assertAlmostEqual(b['revenue_m'],4666.209);self.assertAlmostEqual(b['operating_income_m'],1652.590)
        self.assertAlmostEqual(b['eps'],1484.270/956.860)
    def test_earnings_direction(self):
        self.assertGreater(earnings(volume=.1)['eps'],earnings()['eps'])
        self.assertLess(earnings(inflation=.1)['eps'],earnings()['eps'])
    def test_empty_imports_are_not_evidence(self):
        self.assertEqual(matched_recovery(pd.DataFrame()),{'pairs':0})
        self.assertEqual(coverage(pd.DataFrame(),pd.DataFrame()),[])
        for kind,cols in SCHEMAS.items(): self.assertTrue(validate(kind,pd.DataFrame(columns=cols.split(','))).empty)
import tempfile
from pathlib import Path
from unittest.mock import patch
from src.analysis import imports

class ImportWorkflowTests(unittest.TestCase):
    def test_cli_roundtrip_and_failed_validation_preserves_prior_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'input.csv'
            row=ResearchTests().sale('Copart','private-lot-id')
            pd.DataFrame([row]).to_csv(source,index=False)
            with patch.object(imports,'ROOT',root),patch('sys.argv',['imports','sales',str(source)]):
                imports.main()
                self.assertEqual(imports.load('sales').lot_id.iloc[0],'private-lot-id')
                before=(root/'data/private/sales.csv').read_bytes()
                row['sale_price']=-1;pd.DataFrame([row]).to_csv(source,index=False)
                with self.assertRaises(ValueError): imports.main()
                self.assertEqual((root/'data/private/sales.csv').read_bytes(),before)

if __name__=='__main__': unittest.main()
