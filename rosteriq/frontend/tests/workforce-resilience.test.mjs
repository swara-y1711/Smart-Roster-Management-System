import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("../src/components/workforce-resilience.tsx", import.meta.url), "utf8");

assert.match(source, /Select an employee to run the analysis/);
assert.match(source, /disabled=\{!data\.organization \|\| !employee \|\| busy\}/);
assert.match(source, /No saved assignments for this employee in this period \(0 affected\)\./);
assert.match(source, /No saved roster for \$\{monthLabel\}\. Save a roster in Roster Planner first\./);
assert.match(source, /setError\(apiErrorMessage\(e\)\)/);

console.log("workforce resilience empty-selection and no-saved-roster checks passed");
