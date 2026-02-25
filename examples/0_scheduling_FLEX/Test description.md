# TEST DESCRIPTION

This is an example of EMS input

The use case include:

- 1x electrical load
- 1x thermal load
- 2x natural gas boilers (2x 6MWth)
- 1x CHP unit (2MWel, 1.7MWth)
- 1x BESS (2MW, 4MWh)

Scheduling optimizes Upward Capacity Retention (provided by the BESS and CHP) to support participation in a local flexibility market. The market design follows the Unareti (Milan DSO) local flexibility market model, where power reserves are paid for availability and potential activation during specific time windows (Mon–Thu, 10:00–23:00). Electricity imports follow an Italian 3-level Time-Of-Use tariff, while exports are valued at the NORD zonal DAM price.
