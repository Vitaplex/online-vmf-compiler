import assert from "node:assert/strict";
import test from "node:test";
import { addJobToHistory, parseJobHistory } from "../src/frontend/static/js/jobHistory.js";

test("legacy job IDs are migrated without inventing start dates", () => {
    assert.deepEqual(parseJobHistory('[" old-job ", "other-job", "old-job"]'), [
        { jobId: "old-job", startedAt: null },
        { jobId: "other-job", startedAt: null },
    ]);
});

test("mixed history retains known dates and normalizes them to ISO", () => {
    assert.deepEqual(parseJobHistory(JSON.stringify([
        "job",
        { jobId: "job", startedAt: "2026-11-17T13:00:00+01:00" },
        "job",
    ])), [{ jobId: "job", startedAt: "2026-11-17T12:00:00.000Z" }]);
});

test("new compile jobs save their start date and appear first", () => {
    const previous = [{ jobId: "old-job", startedAt: null }];
    assert.deepEqual(addJobToHistory(previous, "new-job", "2026-11-17T12:00:00Z"), [
        { jobId: "new-job", startedAt: "2026-11-17T12:00:00.000Z" },
        ...previous,
    ]);
    assert.equal(previous.length, 1);
});

test("reopening a known job does not overwrite its original start date", () => {
    const previous = [{ jobId: "job", startedAt: "2026-11-17T12:00:00.000Z" }];
    assert.equal(addJobToHistory(previous, "job", "2026-11-18T12:00:00Z"), previous);
    assert.equal(addJobToHistory(previous, "job"), previous);
});

test("legacy jobs can get their original start date from backend status", () => {
    const previous = [{ jobId: "job", startedAt: null }, { jobId: "other", startedAt: null }];
    assert.deepEqual(addJobToHistory(previous, "job", "2026-11-16T12:00:00Z"), [
        { jobId: "job", startedAt: "2026-11-16T12:00:00.000Z" },
        previous[1],
    ]);
    assert.equal(previous[0].startedAt, null);
});

test("invalid saved records and dates are rejected explicitly", () => {
    for (const value of ['{}', '[null]', '[""]', '[{"jobId":"job","startedAt":"invalid"}]']) {
        assert.throws(() => parseJobHistory(value));
    }
    assert.throws(() => addJobToHistory([], "job", "invalid"));
});
