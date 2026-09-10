# Step 8 Scenario Validation

Unity 6000.6.0f1 / PhysX / model hull 70×50 mm. These are simulated times for the tested configurations.

| Scenario | Result | Rescued | Simulated duration | Maximum passengers per boat | Boat contact-enter events |
| --- | --- | ---: | ---: | ---: | ---: |
| Calm, four boats | Complete | 24/24 | 86.05 s | 6 | 0 |
| Street current, four boats | Complete | 24/24 | 73.82 s | 6 | 0 |
| Street current, three available boats | Complete | 24/24 | 151.22 s | 6 | 0 |
| Shallow preset | Navigation rejected | 0/24 | 12.00 s observation | 0 | 0 |
| High-water preset | Partial, observation time limit reached | 0/24 delivered | 35.00 s observation | 5 | 0 |

All five runs maintained person-count conservation, boat capacity limits and rigidbody mass consistency. The high-water check passes those invariants only; it is not evidence of complete rescue under high water. Its zero delivered count does not mean no boarding occurred: boats carried up to five people during the observation window.

Machine-readable results: `Step8_Validation_Report.json`. Runtime UI and report-export validation is reported separately in `Step8_Runtime_Report.json`.
