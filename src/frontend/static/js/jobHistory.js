export function parseJobHistory(storedHistory) {
    const storedJobs = JSON.parse(storedHistory ?? "[]");
    if (!Array.isArray(storedJobs)) {
        throw new Error("Stored job history must be a list of jobs");
    }

    const jobs = new Map();
    for (const entry of storedJobs) {
        const job = typeof entry === "string" ? { jobId: entry, startedAt: null } : entry;
        if (!job || typeof job.jobId !== "string" || !job.jobId.trim()) {
            throw new Error("Stored jobs must have a job ID");
        }
        const jobId = job.jobId.trim();
        const startedAt = normalizeStartDate(job.startedAt ?? null);
        if (!jobs.has(jobId) || !jobs.get(jobId).startedAt) {
            jobs.set(jobId, { jobId, startedAt });
        }
    }
    return [...jobs.values()];
}

export function addJobToHistory(jobs, jobId, startedAt = null) {
    const existing = jobs.find(job => job.jobId === jobId);
    if (existing && (existing.startedAt || !startedAt)) return jobs;

    const job = { jobId, startedAt: normalizeStartDate(startedAt) };
    return existing
        ? jobs.map(entry => entry.jobId === jobId ? job : entry)
        : [job, ...jobs];
}

function normalizeStartDate(startedAt) {
    if (startedAt === null) return null;
    if (typeof startedAt !== "string" || !Number.isFinite(Date.parse(startedAt))) {
        throw new Error("Job start dates must be valid date strings");
    }
    return new Date(startedAt).toISOString();
}
