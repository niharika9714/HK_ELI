"""Fixed public diagnostics; never forward arbitrary upstream exception text."""
MESSAGES={
    'fixture_scenario_required':'Offline fixture mode accepts Q1 through Q9 or an explicit typed plan. Configure live Stork for natural-language planning.',
    'stork_sdk_missing':'Install the company-approved private ada_genai SDK and configure its authentication.',
    'no_matching_asset':'No unique configured workbook/view was discovered. Check exact published metadata and authorization.',
    'native_control_unsupported':'Requested native field/value is not verified. No unfiltered substitute was produced.',
    'export_contract_unverified':'The original view can be displayed, but its CSV grain/schema has not been reviewed for calculation.',
    'detail_grain_unavailable':'Required detail grain or equivalent authorized detail scope is unavailable; summary rows cannot stand for deals.',
    'export_scope_unverified':'Parameters or highlights cannot be reproduced by this REST export; no mismatched report was produced.',
    'reporting_metadata_missing':'A reviewed reporting date and currency are required for numerical analysis.',
    'analysis_contract_rejected':'The requested calculation violates the reviewed column, grain, null, snapshot or aggregation contract.',
    'tableau_http_failure':'Tableau returned an unsuccessful response; no alternative chart or financial claim was substituted.',
    'capacity_exceeded':'The bounded operation exceeded its configured capacity; narrow the scope. No partial totals were produced.'
}

class PublicError(ValueError):
    def __init__(self,code):
        if code not in MESSAGES:raise ValueError('Unknown diagnostic code.')
        self.code=code;super().__init__(MESSAGES[code])
