/* =====================================================
   GOVERNMENT JOB TRACKER
   MAIN JAVASCRIPT
===================================================== */


/* =====================================================
   LOAD JOB DATA
===================================================== */

async function loadJobs() {

    try {

        const response = await fetch("jobs.json");

        if (!response.ok) {
            throw new Error(
                `HTTP error: ${response.status}`
            );
        }

        const data = await response.json();

        const jobs = Array.isArray(data.jobs)
            ? data.jobs
            : [];

        displayLastUpdated(
            data.last_updated
        );

        displayJobs(
            jobs
        );

    } catch (error) {

        console.error(
            "Unable to load jobs:",
            error
        );

        showError();

    }
}


/* =====================================================
   DISPLAY LAST UPDATED
===================================================== */

function displayLastUpdated(value) {

    const element =
        document.getElementById(
            "last-updated"
        );

    if (!element) {
        return;
    }

    if (!value) {

        element.textContent =
            "Job data loaded";

        return;
    }

    const date =
        new Date(value);

    if (isNaN(date.getTime())) {

        element.textContent =
            "Job data loaded";

        return;
    }

    element.textContent =
        "Last updated: " +
        date.toLocaleString(
            "en-IN",
            {
                dateStyle: "medium",
                timeStyle: "short"
            }
        );
}


/* =====================================================
   DISPLAY ALL JOBS
===================================================== */

function displayJobs(jobs) {

    const critical =
        jobs.filter(
            job => job.status === "critical"
        );

    const open =
        jobs.filter(
            job => job.status === "open"
        );

    const upcoming =
        jobs.filter(
            job => job.status === "upcoming"
        );


    /* -------------------------------------------------
       UPDATE COUNTS
    ------------------------------------------------- */

    updateCount(
        "critical-count",
        critical.length
    );

    updateCount(
        "open-count",
        open.length
    );

    updateCount(
        "upcoming-count",
        upcoming.length
    );


    /* -------------------------------------------------
       RENDER
    ------------------------------------------------- */

    renderJobs(
        "critical-jobs",
        critical,
        "critical"
    );

    renderJobs(
        "open-jobs",
        open,
        "open"
    );

    renderJobs(
        "upcoming-jobs",
        upcoming,
        "upcoming"
    );
}


/* =====================================================
   UPDATE COUNT
===================================================== */

function updateCount(
    elementId,
    count
) {

    const element =
        document.getElementById(
            elementId
        );

    if (element) {

        element.textContent =
            count;
    }
}


/* =====================================================
   RENDER JOBS
===================================================== */

function renderJobs(
    containerId,
    jobs,
    status
) {

    const container =
        document.getElementById(
            containerId
        );

    if (!container) {
        return;
    }


    /* -------------------------------------------------
       EMPTY
    ------------------------------------------------- */

    if (jobs.length === 0) {

        container.innerHTML = `
            <div class="empty-message">
                No jobs in this section right now.
            </div>
        `;

        return;
    }


    /* -------------------------------------------------
       CREATE CARDS
    ------------------------------------------------- */

    container.innerHTML =
        jobs.map(
            job => createJobCard(
                job,
                status
            )
        ).join("");
}


/* =====================================================
   CREATE JOB CARD
===================================================== */

function createJobCard(
    job,
    status
) {

    const title =
        escapeHTML(
            job.title ||
            "Government Job"
        );

    const url =
        safeURL(
            job.url
        );


    /* -------------------------------------------------
       STATUS
    ------------------------------------------------- */

    const statusText =
        getStatusText(
            status
        );


    /* -------------------------------------------------
       DATES
    ------------------------------------------------- */

    const startDate =
        formatDate(
            job.application_start
        );

    const endDate =
        formatDate(
            job.application_end
        );


    /* -------------------------------------------------
       POSTS
    ------------------------------------------------- */

    const posts =
        formatPosts(
            job.posts
        );


    /* -------------------------------------------------
       DAYS LEFT
    ------------------------------------------------- */

    let daysLeftHTML = "";

    if (
        typeof job.days_left === "number" &&
        job.application_end
    ) {

        const days =
            job.days_left;

        if (days < 0) {

            daysLeftHTML = `
                <div class="days-left">
                    Application closed
                </div>
            `;

        } else if (days === 0) {

            daysLeftHTML = `
                <div class="days-left urgent">
                    ⚠️ Last day to apply
                </div>
            `;

        } else if (days === 1) {

            daysLeftHTML = `
                <div class="days-left urgent">
                    ⚠️ 1 day left
                </div>
            `;

        } else if (days <= 5) {

            daysLeftHTML = `
                <div class="days-left urgent">
                    ⚠️ ${days} days left
                </div>
            `;

        } else {

            daysLeftHTML = `
                <div class="days-left">
                    ${days} days left
                </div>
            `;
        }
    }


    /* -------------------------------------------------
       APPLY BUTTON
    ------------------------------------------------- */

    let applyButton = "";

    if (url) {

        applyButton = `
            <a
                class="apply-button"
                href="${url}"
                target="_blank"
                rel="noopener noreferrer"
            >
                View Details →
            </a>
        `;
    }


    /* -------------------------------------------------
       CARD
    ------------------------------------------------- */

    return `
        <article class="job-card">

            <span
                class="status-badge status-${status}"
            >
                ${statusText}
            </span>

            <h3 class="job-title">

                ${
                    url
                    ? `
                        <a
                            href="${url}"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            ${title}
                        </a>
                    `
                    : title
                }

            </h3>


            <div class="job-details">

                ${
                    startDate
                    ? `
                        <div class="detail">

                            <span class="detail-label">
                                Application starts
                            </span>

                            <span class="detail-value">
                                ${startDate}
                            </span>

                        </div>
                    `
                    : ""
                }


                ${
                    endDate
                    ? `
                        <div class="detail">

                            <span class="detail-label">
                                Last date
                            </span>

                            <span class="detail-value deadline">
                                ${endDate}
                            </span>

                        </div>
                    `
                    : ""
                }


                ${
                    posts
                    ? `
                        <div class="detail">

                            <span class="detail-label">
                                Vacancies
                            </span>

                            <span class="detail-value">
                                ${posts}
                            </span>

                        </div>
                    `
                    : ""
                }

            </div>


            ${daysLeftHTML}

            ${applyButton}

        </article>
    `;
}


/* =====================================================
   STATUS TEXT
===================================================== */

function getStatusText(
    status
) {

    switch (status) {

        case "critical":
            return "Closing Soon";

        case "open":
            return "Application Open";

        case "upcoming":
            return "Upcoming";

        case "old":
            return "Expired";

        default:
            return "Status Unknown";
    }
}


/* =====================================================
   FORMAT DATE
===================================================== */

function formatDate(
    value
) {

    if (!value) {
        return "";
    }

    const date =
        new Date(
            value + "T00:00:00"
        );

    if (
        isNaN(
            date.getTime()
        )
    ) {

        return escapeHTML(
            value
        );
    }

    return date.toLocaleDateString(
        "en-IN",
        {
            day: "2-digit",
            month: "short",
            year: "numeric"
        }
    );
}


/* =====================================================
   FORMAT POSTS
===================================================== */

function formatPosts(
    value
) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {

        return "";
    }

    const number =
        Number(value);

    if (
        Number.isFinite(number)
    ) {

        return number.toLocaleString(
            "en-IN"
        );
    }

    return escapeHTML(
        String(value)
    );
}


/* =====================================================
   SAFE URL
===================================================== */

function safeURL(
    value
) {

    if (!value) {
        return "";
    }

    try {

        const url =
            new URL(
                value,
                window.location.origin
            );

        if (
            url.protocol === "https:" ||
            url.protocol === "http:"
        ) {

            return escapeAttribute(
                url.href
            );
        }

    } catch (error) {

        console.warn(
            "Invalid URL:",
            value
        );
    }

    return "";
}


/* =====================================================
   ESCAPE HTML
===================================================== */

function escapeHTML(
    value
) {

    return String(value)
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );
}


/* =====================================================
   ESCAPE ATTRIBUTE
===================================================== */

function escapeAttribute(
    value
) {

    return escapeHTML(
        value
    );
}


/* =====================================================
   SHOW ERROR
===================================================== */

function showError() {

    const error =
        document.getElementById(
            "error-message"
        );

    if (error) {

        error.classList.remove(
            "hidden"
        );
    }


    const containers = [
        "critical-jobs",
        "open-jobs",
        "upcoming-jobs"
    ];

    containers.forEach(
        id => {

            const container =
                document.getElementById(
                    id
                );

            if (container) {

                container.innerHTML = `
                    <div class="empty-message">
                        Job data could not be loaded.
                    </div>
                `;
            }
        }
    );
}


/* =====================================================
   START
===================================================== */

document.addEventListener(
    "DOMContentLoaded",
    loadJobs
);
