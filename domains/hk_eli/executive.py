"""Deterministic 14-section draft; missing metrics stay explicit."""
TITLES=['Executive Summary','As-of Business Date','Business Financials','Sales Momentum',
        'Top Underlying and Sector','RFQ Demand Analysis','Worst-of Underlying Exposure',
        'Stock Concentration','Exercise Stock Analysis','Maturity Calendar','Rollover Summary',
        'Customer Status','Management Actions','Executive Conclusion']
METRICS=[['sales','notional'],[],['sales','revenue'],['sales'],['notional'],['rfqs','won','conversion'],
         ['worst_of_notional'],['share'],[],['deals','notional'],['opportunities'],['clients','events'],[],[]]

def build(evidence):
    sections=[]
    for title,metrics in zip(TITLES,METRICS):
        selected=[e for e in evidence if e.metric in metrics][:8]
        if title=='As-of Business Date':
            selected=evidence[:1]
            content='Reporting dates: '+', '.join(sorted({e.as_of for e in evidence}))
        elif title=='Exercise Stock Analysis':content='Unavailable: no confirmed exercise-event definition or authorized exercise history.'
        elif title=='Management Actions':content='Draft review only. Validate synthetic assumptions and the cited concentrations, maturity and rollover scope with business owners.'
        elif title=='Executive Conclusion':content='Synthetic demonstration supports review of defined fixture metrics. Production readiness requires live integration checks and business sign-off.'
        elif selected:content='; '.join(f'{e.metric}: {e.value} {e.unit} ({", ".join(e.dimensions.values())}) [{e.id}]' for e in selected)
        else:content='Unavailable: no verified evidence for this requested section.'
        sections.append({'title':title,'content':content,'evidence_ids':[e.id for e in selected],
            'limitations':['Sector look-through is not available in this concentration output.'] if title=='Top Underlying and Sector' else []})
    return sections
