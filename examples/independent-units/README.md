# Independent-unit planning fixture

This fixture demonstrates three independent declared units in one Bolt and four tickets.
It is NOT a completed application, and the test commands are illustrative, not evidence of passes.
All units read one frozen record contract and own separate source/test directories.
The three JSON files are deterministic test inputs; implement real contract tests before delivery.

Run the repository helper with `validate --root examples/independent-units` and
`tickets --root examples/independent-units` from the repository root. These commands are offline.
Writes are disabled and no repository is granted. Never enable the example unchanged for production.

Change a contract byte or add a dependency/overlapping owned path to see validation fail.
A successful static check does not prove code or runtime independence.
