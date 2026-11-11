"""Reviewed planner-facing capability guidance. Examples are synthetic, never discovered IDs."""
BUSINESS={
 'eli.sales.performance':('Summarize synthetic sales and revenue by branch in one currency.','Review branch sales or revenue.','Quoted coupon, realized return, live sales or pending pipeline.','Show mock branch sales.'),
 'eli.rfq.conversion':('Calculate synthetic conversion using distinct RFQ IDs, excluding duplicate event rows.','Review mock RFQ demand and won/request ratio.','Pricing, tradeable quotes or sales revenue.','Show synthetic RFQ conversion.'),
 'eli.risk.concentration':('Review top ten synthetic primary-underlying allocations, shares and review flags.','Mock underlying concentration, affected clients or worst-of flagged subset.','Full basket look-through, credit quality, suitability or live risk.','Review mock underlying concentration.'),
 'eli.maturity.analyze':('Aggregate synthetic maturity notional in a fixed as-of date window.','Upcoming mock maturity dates or notional.','Trade-date history, unknown calendars or realized returns.','Show mock maturities within five days.'),
 'eli.rollover.opportunity':('Find synthetic eligible rollover records and their maturity-scoped notional.','Review mock rollover opportunities.','Automatic reinvestment recommendations or executed rollover rates.','Review synthetic rollover opportunities.'),
 'eli.client.engagement':('Count synthetic client engagement events by interaction kind.','Review mock meeting/call activity.','Client holdings, suitability, preferences inferred from behavior.','Summarize mock engagement.'),
 'eli.regional.performance':('Aggregate synthetic sales/revenue using temporally valid district/branch mappings.','Compare mock branch and district performance.','Team contributions or pending pipeline not present in the fixture.','Compare synthetic district sales.'),
 'eli.digibank.journey':('Count distinct synthetic journey events and clients by channel stage.','Review mock digital funnel stages.','Causal attribution or an unapproved customer conversion formula.','Show mock digital journey events.'),
 'eli.product.yield':('Compare synthetic product min/max and notional-weighted quoted coupons.','Compare mock quoted product coupons.','Realized return, performance series, payoff or live yield.','Compare synthetic quoted coupons.'),
 'eli.branch.concentration':('Aggregate mock primary-underlying notional by branch.','Compare synthetic branch allocations.','Full basket risk or cross-currency totals.','Show mock branch concentration.'),
 'eli.client.intelligence':('Aggregate synthetic client/product notional and position counts.','Review mock client product allocations.','Live client balances or suitability recommendations.','Show synthetic client allocations.'),
 'eli.sales.trend':('Return an ordered synthetic dated sales series in a single currency.','Prepare mock sales momentum or a baseline forecast input.','A forecast itself or actual market prediction.','Show mock dated sales trends.')
}


def guidance(name):
    if name in BUSINESS:
        description,use,avoid,question=BUSINESS[name]
        return make(description,use,avoid,question,{},'MOCK only; fixed fixture as-of date, server-derived country and one currency; definitions unapproved.')
    if name.startswith('eli.pricing.solve_'):
        target=name.rsplit('_',1)[-1]
        return make(f'Solve an indicative synthetic {target} using deterministic mock pricing.',
            f'User explicitly requests a synthetic/indicative quote solving {target} with basket and tenor.',
            'Coupon comparisons, existing Tableau charts, live SPE quotes or missing basket/tenor.',
            f'Draft a mock six-month {target} quote for SYN-STOCK0.',{'basket':['SYN-STOCK0'],'tenor_months':6,'solve_target':target},
            'MOCK pricing is not a valuation model or tradeable quote; defaults/expiry disclosed; missing required terms remain unresolved.')
    view={'dashboard':'SYN-DASH','view_id':'SYN-VIEW'}
    tableau={
        'discover':('Discover exact published assets under selected authorized dashboards.','Find available authorized Tableau views.','Semantic matching without reading metadata or invented IDs.'),
        'resolve':('Validate an exact discovered Tableau view and declared native controls.','Check a known selected view/control request.','Discover a guessed view or bypass entitlements.'),
        'embed':('Display an original authorized Tableau view with published defaults or verified controls.','User requests an existing chart/dashboard.','Redraw an original chart, calculate unseen values or ignore requested conditions.'),
        'filter':('Display an original Tableau view with exact reviewed native filter overrides.','User requests a supported original-view filter.','Undeclared fields/values or local-only conditions pretending to be native filters.'),
        'compare':('Display exactly two independent original authorized Tableau views.','User asks to compare/show two original views.','Join independent exports or combine their totals.'),
        'retrieve':('Retrieve a bounded full authorized CSV and return only its profile.','Inspect actual received columns/grain before analysis.','Persist raw rows or assume dashboard CSV covers all components.'),
        'profile':('Profile actual columns, approved additivity and date fields over the full export.','Need observed export capabilities.','Answer a financial question from metadata alone.'),
        'analyze':('Calculate over an authorized CSV using reviewed grain/units and actual observed columns.','Custom charts, aggregation or numerical findings supported by the export.','Invented formulas, inferred deal grain, summed rates or mismatched native/export scope.'),
        'generate':('Narrate executed evidence with validated numerical references.','Explain verified returned results.','Infer numbers from an image or calculate new figures in prose.'),
        'export':('Export the original authorized Tableau chart as PNG for a draft report.','Include an original native chart in a document.','Redraw it or claim unsupported parameter/highlight export equivalence.')}
    if name.startswith('tableau.'):
        action=name.rsplit('.',1)[-1];description,use,avoid=tableau[action]
        params={'dashboards':['SYN-DASH']} if action=='discover' else {'views':[view,view]} if action=='compare' else {'question':'Explain verified evidence'} if action=='generate' else dict(view)
        if action=='analyze':params['analysis']=None
        return make(description,use,avoid,'Show an authorized Tableau view or its supported analysis.',params,
            'Requires discovered IDs and authorized source scope. Original display and CSV calculation are distinct; browser changes do not refresh saved findings.')
    if name.startswith('knowledge.'):
        action=name.rsplit('.',1)[-1]
        params={'query':'reporting date','dashboards':[]}
        if action=='resolve':params['record_id']='SYN-RECORD'
        return make({'search':'Search reference documents for business/source terminology.','retrieve':'Retrieve bounded reference documents and shared business context.','resolve':'Resolve reviewed source definitions by exact record identity.'}[action],
            'Definitions, acronyms, approved source metadata or business context.',
            'Current portfolio figures, financial evidence, granting permissions or approving formulas.',
            'Explain terminology from the reviewed knowledge pack.',params,
            'Reference only; source documents remain scoped; shared definitions are not numerical evidence.')
    if name.startswith('analytics.'):
        action=name.rsplit('.',1)[-1]
        descriptions={'aggregate':'Sum one explicitly additive metric from a declared upstream task.',
            'compare':'Compare min/max/difference within one upstream metric and scope.',
            'trend':'Present a unique ascending ISO-date upstream series.',
            'rank':'Sort an upstream metric descending with an explicitly requested limit.',
            'anomaly':'Flag descriptive deviations above three population standard deviations.',
            'forecast':'Produce a naive last-observation baseline estimate from an ordered date series.'}
        params={'source_task':'source','column':'value','operation':'sum' if action=='aggregate' else action}
        if action in ('forecast','trend'):params['date_column']='date'
        return make(descriptions[action],f'Explicitly requested {action} over a declared validated upstream metric.',
            'Fetching new data, mixed LIVE/MOCK arithmetic, unapproved units/additivity or investment prediction.',
            f'Apply {action} to the validated synthetic source metric.',params,
            'Declare source_task as a dependency; preserve one source mode, unit and reporting date. Forecasts/anomalies are descriptive estimates, not advice.')
    if name.startswith('artifact.'):
        action=name.rsplit('.',1)[-1]
        return make({'generate':'Record a document request for the final evidence-linked draft builder; does not render files during task execution.','validate':'Check ownership, expiry and integrity of an existing protected draft.','publish_draft':'Validate an existing artifact and retain draft status; does not distribute it.'}[action],
            'User requests a supported draft document or validation of an owned artifact.',
            'Sending email, external publication, inventing figures or bypassing artifact ownership.',
            'Prepare a PDF draft from the executed evidence.',{'formats':['pdf']} if action=='generate' else {'artifact_id':'SYN-ARTIFACT'},
            'DOCX/PPTX/PDF/XLSX only; unspecified format must remain empty and triggers format clarification, never a PDF default. Current permissions/evidence/ownership/TTL apply; human approval remains pending.')
    return make('Execute a custom registered operation under its declared typed contract.','Explicitly documented custom capability.','Undocumented assumptions.', 'Consult the custom contract.',{},'No implicit financial authority.')


def make(description,use,avoid,question,parameters,limitation):
    return {'description':description,'use_when':[use],'do_not_use_when':[avoid],
            'examples':[{'question':question,'parameters':parameters,'synthetic_example':True}],
            'limitations':[limitation],'capabilities':[description]}
