(() => {
  const form=document.getElementById('research-controls');
  if(!form) return;
  const b=JSON.parse(document.getElementById('earnings-baseline').textContent);
  const out=document.getElementById('research-output');
  function update(){
    if(!form.checkValidity()){out.textContent='Enter values within the displayed bounds.';return;}
    const n=name=>Number(form.elements[name].value)/100;
    const supply=100*(1+n('exposure'))**5*(1+n('claims'))**5*n('tlf')/.22;
    const v=n('volume'),r=n('rpu'),i=n('inflation');
    const revenue=b.service*(1+v)*(1+r)+b.vehicle*(1+v);
    const op=revenue-b.facility*(.4+.6*(1+v))*(1+i)-b.vehicle_cost*(1+v)-b.other_cost*(1+i);
    const eps=((op+b.interest+b.other_income)*(1-b.tax_rate)+b.nci_loss)/b.shares;
    out.textContent=`Five-year industry supply index: ${supply.toFixed(1)} (start 100). One-year Copart EPS sensitivity: $${eps.toFixed(2)}; operating margin: ${(100*op/revenue).toFixed(1)}%.`;
  }
  form.addEventListener('input',update);form.addEventListener('submit',e=>e.preventDefault());update();
})();
