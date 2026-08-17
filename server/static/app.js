// Super Admin SaaS Dashboard Frontend Controller - with Video Processing Analytics & Modern Lucide Icons
let currentAdminToken = localStorage.getItem("dola_admin_token") || null;
let currentUsers = [];
let currentAnalytics = null;
let activeFilter = "all";
let targetUserIdToApprove = null;
let currentActiveTab = "users";

// DOM Elements
const loginSection = document.getElementById("loginSection");
const dashboardSection = document.getElementById("dashboardSection");
const adminLoginForm = document.getElementById("adminLoginForm");
const loginError = document.getElementById("loginError");
const userTableBody = document.getElementById("userTableBody");
const searchInput = document.getElementById("searchInput");
const refreshBtn = document.getElementById("refreshBtn");
const logoutBtn = document.getElementById("logoutBtn");
const approveModal = document.getElementById("approveModal");
const modalUserEmail = document.getElementById("modalUserEmail");
const modalUserName = document.getElementById("modalUserName");
const modalUserHwid = document.getElementById("modalUserHwid");
const customDateGroup = document.getElementById("customDateGroup");
const customExpiryDate = document.getElementById("customExpiryDate");
const adminNotes = document.getElementById("adminNotes");
const approveForm = document.getElementById("approveForm");
const planSelect = document.getElementById("planSelect");

// Initial Startup
document.addEventListener("DOMContentLoaded", () => {
    if (currentAdminToken) {
        showDashboard();
    } else {
        showLogin();
    }
    setupEventListeners();
    refreshIcons();
});

function refreshIcons() {
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

function setupEventListeners() {
    // Admin Login Form
    adminLoginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("adminUsername").value.trim();
        const password = document.getElementById("adminPassword").value.trim();
        
        loginError.classList.add("hidden");
        try {
            const res = await fetch("/api/admin/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Login failed");
            
            currentAdminToken = data.token;
            localStorage.setItem("dola_admin_token", currentAdminToken);
            document.getElementById("displayAdminUser").textContent = username;
            showDashboard();
            showToast("Welcome back, Super Admin!", "success");
        } catch (err) {
            loginError.textContent = err.message;
            loginError.classList.remove("hidden");
        }
    });

    // Logout
    logoutBtn.addEventListener("click", () => {
        localStorage.removeItem("dola_admin_token");
        currentAdminToken = null;
        showLogin();
        showToast("Logged out successfully", "info");
    });

    // Refresh
    refreshBtn.addEventListener("click", () => {
        loadDashboardData();
        showToast("Data refreshed", "info");
    });

    // Search Input
    searchInput.addEventListener("input", () => {
        renderUsers();
    });

    // Filter Buttons
    document.querySelectorAll(".filter-pills .filter-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            document.querySelectorAll(".filter-pills .filter-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            activeFilter = btn.dataset.status;
            renderUsers();
        });
    });

    // Approve / License Update Form Submission
    approveForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!targetUserIdToApprove) return;

        const selectedPlan = planSelect.value;
        const customDate = selectedPlan === "custom" ? customExpiryDate.value : null;
        const notes = adminNotes.value.trim();

        if (selectedPlan === "custom" && !customDate) {
            alert("Please select a custom expiration date.");
            return;
        }

        const savePlanBtn = document.getElementById("savePlanBtn");
        savePlanBtn.disabled = true;

        try {
            await apiRequest(`/api/admin/users/${targetUserIdToApprove}/approve`, "POST", {
                plan_type: selectedPlan,
                custom_date: customDate,
                notes: notes
            });
            closeApproveModal();
            showToast("License plan updated successfully!", "success");
            loadDashboardData();
        } catch (err) {
            alert("Error approving user: " + err.message);
        } finally {
            savePlanBtn.disabled = false;
        }
    });
}

function handlePlanChange() {
    if (planSelect.value === "custom") {
        customDateGroup.classList.remove("hidden");
    } else {
        customDateGroup.classList.add("hidden");
    }
}

function switchDashboardTab(tab) {
    currentActiveTab = tab;
    const viewUsers = document.getElementById("viewUsersSection");
    const viewAnalytics = document.getElementById("viewAnalyticsSection");
    const tabBtnUsers = document.getElementById("tabBtnUsers");
    const tabBtnAnalytics = document.getElementById("tabBtnAnalytics");

    if (tab === "users") {
        viewUsers.classList.remove("hidden");
        viewAnalytics.classList.add("hidden");
        tabBtnUsers.classList.add("active");
        tabBtnAnalytics.classList.remove("active");
    } else {
        viewUsers.classList.add("hidden");
        viewAnalytics.classList.remove("hidden");
        tabBtnUsers.classList.remove("active");
        tabBtnAnalytics.classList.add("active");
        loadAnalyticsData();
    }
    refreshIcons();
}

function showLogin() {
    loginSection.classList.remove("hidden");
    dashboardSection.classList.add("hidden");
    refreshIcons();
}

function showDashboard() {
    loginSection.classList.add("hidden");
    dashboardSection.classList.remove("hidden");
    loadDashboardData();
    refreshIcons();
}

async function apiRequest(endpoint, method = "GET", body = null) {
    const headers = {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentAdminToken}`
    };
    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);
    
    const res = await fetch(endpoint, options);
    if (res.status === 401 || res.status === 403) {
        localStorage.removeItem("dola_admin_token");
        currentAdminToken = null;
        showLogin();
        throw new Error("Session expired. Please log in again.");
    }
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Request failed");
    return data;
}

async function loadDashboardData() {
    try {
        const [stats, usersData, analyticsData] = await Promise.all([
            apiRequest("/api/admin/stats"),
            apiRequest("/api/admin/users"),
            apiRequest("/api/admin/analytics")
        ]);
        
        // Update Video Processing Hero Metrics
        document.getElementById("statWatermarks").textContent = (analyticsData.total_watermarks_removed || 0).toLocaleString();
        document.getElementById("statWatermarksToday").textContent = (analyticsData.today_watermarks || 0).toLocaleString();
        
        document.getElementById("statCombines").textContent = (analyticsData.total_videos_combined || 0).toLocaleString();
        document.getElementById("statCombinesToday").textContent = (analyticsData.today_combines || 0).toLocaleString();
        
        document.getElementById("statActive").textContent = stats.active || 0;
        document.getElementById("statActiveToday").textContent = (analyticsData.active_users_today || 0);
        
        document.getElementById("statPending").textContent = stats.pending || 0;
        document.getElementById("statTotalUsers").textContent = stats.total || 0;
        
        document.getElementById("countAll").textContent = stats.total || 0;
        document.getElementById("countPending").textContent = stats.pending || 0;
        document.getElementById("countTabUsers").textContent = stats.total || 0;

        currentUsers = usersData.users || [];
        currentAnalytics = analyticsData;

        renderUsers();
        renderAnalyticsViews(analyticsData);
    } catch (err) {
        console.error(err);
    }
}

async function loadAnalyticsData() {
    try {
        const analyticsData = await apiRequest("/api/admin/analytics");
        currentAnalytics = analyticsData;
        renderAnalyticsViews(analyticsData);
        showToast("Analytics feed updated", "info");
    } catch (err) {
        console.error(err);
    }
}

function renderAnalyticsViews(data) {
    if (!data) return;

    // 1. Leaderboard
    const lbBody = document.getElementById("leaderboardBody");
    const topUsers = data.top_users || [];
    if (topUsers.length === 0) {
        lbBody.innerHTML = `<tr><td colspan="5" class="empty-state" style="text-align:center; padding: 24px; color: var(--text-muted);">No video operations recorded yet.</td></tr>`;
    } else {
        lbBody.innerHTML = topUsers.map((u, idx) => {
            const rankBadge = idx === 0 
                ? `<span style="color:#fbbf24; font-weight:800; margin-right:4px;">#1</span>`
                : idx === 1 
                ? `<span style="color:#94a3b8; font-weight:800; margin-right:4px;">#2</span>`
                : idx === 2
                ? `<span style="color:#b45309; font-weight:800; margin-right:4px;">#3</span>`
                : `<span style="color:var(--text-muted); font-size:11px; margin-right:4px;">#${idx+1}</span>`;

            return `
                <tr>
                    <td>
                        <div style="display:flex; align-items:center;">
                            ${rankBadge}
                            <div>
                                <strong>${escapeHtml(u.full_name || 'Anonymous')}</strong>
                                <div style="font-size: 11px; color: var(--text-muted);">${escapeHtml(u.email)}</div>
                            </div>
                        </div>
                    </td>
                    <td><span class="badge" style="font-size:11px;">${formatPlanName(u.plan_type)}</span></td>
                    <td><strong style="color: #a5b4fc;">${u.watermark_count || 0}</strong></td>
                    <td><strong style="color: #60a5fa;">${u.combine_count || 0}</strong></td>
                    <td><strong style="color: #10b981;">${u.total_ops_count || 0}</strong></td>
                </tr>
            `;
        }).join("");
    }

    // 2. Activity Feed
    const feedList = document.getElementById("activityFeedList");
    const activities = data.recent_activities || [];
    if (activities.length === 0) {
        feedList.innerHTML = `<div class="empty-state" style="text-align:center; padding: 24px; color: var(--text-muted);">No recent video processing activity.</div>`;
    } else {
        feedList.innerHTML = activities.map(act => {
            const isWm = act.op_type.includes("watermark");
            const iconName = isWm ? "wand-2" : "film";
            const iconColor = isWm ? "#818cf8" : "#60a5fa";
            const typeLabel = isWm ? "Watermark Removal" : "Video Combine";
            const timeAgo = formatTimeAgo(act.created_at);

            return `
                <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; padding: 10px 14px; display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="background: rgba(255,255,255,0.05); padding: 8px; border-radius: 6px; display: flex; align-items: center; justify-content: center;">
                            <i data-lucide="${iconName}" style="width:18px; height:18px; color:${iconColor};"></i>
                        </div>
                        <div>
                            <div style="font-size: 13px; font-weight: 600; color: #ffffff;">
                                ${escapeHtml(act.email)}
                                <span style="font-size: 11px; margin-left: 6px; padding: 2px 6px; border-radius: 4px; background: rgba(99,102,241,0.15); color:#a5b4fc;">${typeLabel}</span>
                            </div>
                            <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">
                                ${escapeHtml(act.details || (act.item_count + ' items processed'))}
                            </div>
                        </div>
                    </div>
                    <div style="font-size: 11px; color: #9ca3af; text-align: right;">
                        <strong>${act.item_count} clip(s)</strong><br>
                        ${timeAgo}
                    </div>
                </div>
            `;
        }).join("");
    }
    refreshIcons();
}

function renderUsers() {
    const searchTerm = searchInput.value.toLowerCase().trim();
    
    const filtered = currentUsers.filter(user => {
        if (activeFilter !== "all" && user.status !== activeFilter) {
            return false;
        }
        if (searchTerm) {
            const matchesEmail = user.email && user.email.toLowerCase().includes(searchTerm);
            const matchesName = user.full_name && user.full_name.toLowerCase().includes(searchTerm);
            const matchesHwid = user.hwid && user.hwid.toLowerCase().includes(searchTerm);
            if (!matchesEmail && !matchesName && !matchesHwid) return false;
        }
        return true;
    });

    if (filtered.length === 0) {
        userTableBody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-state" style="text-align:center; padding: 40px; color: var(--text-muted);">
                    No users found matching your criteria.
                </td>
            </tr>
        `;
        refreshIcons();
        return;
    }

    userTableBody.innerHTML = filtered.map(user => {
        const statusBadge = getStatusBadge(user.status);
        const planName = formatPlanName(user.plan_type);
        const expiryFormatted = formatExpiry(user.expires_at, user.plan_type);
        const hwidCell = formatHwid(user.hwid);
        const registeredDate = user.created_at ? new Date(user.created_at).toLocaleDateString() : "-";
        const emailVerifiedBadge = user.is_email_verified === 1 
            ? `<span style="font-size:10px; color:#10b981; margin-left:4px; display:inline-flex; align-items:center; gap:2px;" title="Email Verified"><i data-lucide="check-circle" style="width:12px; height:12px;"></i> Verified</span>`
            : `<span style="font-size:10px; color:#fbbf24; margin-left:4px; display:inline-flex; align-items:center; gap:2px;" title="Email Unverified"><i data-lucide="mail" style="width:12px; height:12px;"></i> Unverified</span>`;

        const wmCount = user.watermark_count || 0;
        const combCount = user.combine_count || 0;
        const usageCell = `
            <div style="font-size: 12px; line-height: 1.4; display:flex; align-items:center; gap:8px;">
                <span style="color: #a5b4fc; font-weight: 600; display:inline-flex; align-items:center; gap:3px;" title="Watermarks Removed">
                    <i data-lucide="wand-2" style="width:12px; height:12px;"></i> ${wmCount}
                </span>
                <span style="color: #60a5fa; font-weight: 600; display:inline-flex; align-items:center; gap:3px;" title="Videos Combined">
                    <i data-lucide="film" style="width:12px; height:12px;"></i> ${combCount}
                </span>
            </div>
        `;

        return `
            <tr>
                <td>
                    <div class="user-name-col">${escapeHtml(user.full_name || 'Anonymous')} ${emailVerifiedBadge}</div>
                    <div class="user-email-sub">${escapeHtml(user.email)}</div>
                </td>
                <td>${statusBadge}</td>
                <td>
                    <button class="btn btn-outline btn-xs" style="font-weight:700; color: #a5b4fc; border-color: rgba(99,102,241,0.3); background: rgba(99,102,241,0.08); display:inline-flex; align-items:center; gap:4px;" title="Click to Change Plan" onclick="openApproveModal(${user.id}, '${escapeHtml(user.email)}', '${escapeHtml(user.full_name || '')}', '${escapeHtml(user.hwid || '')}', '${user.plan_type}')">
                        <span>${planName}</span>
                        <i data-lucide="edit-3" style="width:11px; height:11px;"></i>
                    </button>
                </td>
                <td>${usageCell}</td>
                <td>${expiryFormatted}</td>
                <td>${hwidCell}</td>
                <td style="color: var(--text-muted); font-size: 13px;">${registeredDate}</td>
                <td class="text-right">
                    <div class="action-group" style="justify-content: flex-end;">
                        <button class="btn btn-emerald btn-xs" style="font-weight:700; padding: 6px 12px; display:inline-flex; align-items:center; gap:4px;" onclick="openApproveModal(${user.id}, '${escapeHtml(user.email)}', '${escapeHtml(user.full_name || '')}', '${escapeHtml(user.hwid || '')}', '${user.plan_type}')">
                            <i data-lucide="zap" style="width:12px; height:12px;"></i>
                            <span>${user.status === 'active' ? 'Change Plan' : 'Approve'}</span>
                        </button>
                        ${user.hwid ? `
                            <button class="btn btn-outline btn-xs" title="Unbind PC hardware ID so user can switch device" style="display:inline-flex; align-items:center; gap:4px;" onclick="resetUserHwid(${user.id}, '${escapeHtml(user.email)}')">
                                <i data-lucide="unlock" style="width:12px; height:12px;"></i>
                                <span>Reset HWID</span>
                            </button>
                        ` : ''}
                        ${user.status === 'active' ? `
                            <button class="btn btn-outline btn-xs text-rose" style="display:inline-flex; align-items:center; gap:4px;" onclick="setUserStatus(${user.id}, 'suspended')">
                                <i data-lucide="pause-circle" style="width:12px; height:12px;"></i>
                                <span>Suspend</span>
                            </button>
                        ` : user.status === 'suspended' ? `
                            <button class="btn btn-outline btn-xs text-emerald" style="display:inline-flex; align-items:center; gap:4px;" onclick="setUserStatus(${user.id}, 'active')">
                                <i data-lucide="play-circle" style="width:12px; height:12px;"></i>
                                <span>Reactivate</span>
                            </button>
                        ` : ''}
                        <button class="btn btn-outline btn-xs" title="Delete User" style="color: #ef4444;" onclick="deleteUser(${user.id}, '${escapeHtml(user.email)}')">
                            <i data-lucide="trash-2" style="width:12px; height:12px;"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join("");
    refreshIcons();
}

function getStatusBadge(status) {
    switch (status) {
        case "pending":
            return `<span class="badge badge-pending" style="display:inline-flex; align-items:center; gap:4px;"><i data-lucide="clock" style="width:11px; height:11px;"></i> Pending</span>`;
        case "active":
            return `<span class="badge badge-active" style="display:inline-flex; align-items:center; gap:4px;"><i data-lucide="check-circle-2" style="width:11px; height:11px;"></i> Active</span>`;
        case "expired":
            return `<span class="badge badge-expired" style="display:inline-flex; align-items:center; gap:4px;"><i data-lucide="alert-triangle" style="width:11px; height:11px;"></i> Expired</span>`;
        case "suspended":
            return `<span class="badge badge-suspended" style="display:inline-flex; align-items:center; gap:4px;"><i data-lucide="pause-circle" style="width:11px; height:11px;"></i> Suspended</span>`;
        default:
            return `<span class="badge">${status}</span>`;
    }
}

function formatPlanName(plan) {
    switch (plan) {
        case "7_days": return "7 Days Trial";
        case "1_month": return "1 Month";
        case "1_year": return "1 Year";
        case "lifetime": return "Lifetime Pro";
        case "custom": return "Custom Plan";
        default: return "None";
    }
}

function formatExpiry(expires_at, plan_type) {
    if (plan_type === "lifetime") {
        return `<span class="text-emerald" style="font-weight:600; display:inline-flex; align-items:center; gap:4px;"><i data-lucide="infinity" style="width:14px; height:14px;"></i> Lifetime</span>`;
    }
    if (!expires_at) return `<span style="color:var(--text-dim);">-</span>`;
    
    const expDate = new Date(expires_at);
    const now = new Date();
    const diffMs = expDate - now;
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays < 0) {
        return `<span class="text-rose">Expired (${expDate.toLocaleDateString()})</span>`;
    } else if (diffDays === 0) {
        return `<span class="text-amber">Expires today</span>`;
    } else if (diffDays <= 7) {
        return `<span class="text-amber"><strong>${diffDays} days left</strong></span>`;
    } else {
        return `<span>${diffDays} days left</span>`;
    }
}

function formatHwid(hwid) {
    if (!hwid) {
        return `<span class="hwid-unbound">Not Bound Yet</span>`;
    }
    return `<span class="hwid-badge" title="${escapeHtml(hwid)}"><i data-lucide="lock" style="width:11px; height:11px; margin-right:4px;"></i>${escapeHtml(hwid)}</span>`;
}

function formatTimeAgo(isoString) {
    if (!isoString) return "";
    const date = new Date(isoString);
    const seconds = Math.floor((new Date() - date) / 1000);
    if (seconds < 60) return "just now";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

function openApproveModal(userId, email, fullName = "", hwid = "", currentPlan = "lifetime") {
    targetUserIdToApprove = userId;
    modalUserEmail.textContent = email;
    modalUserName.textContent = fullName || "Not set";
    modalUserHwid.textContent = hwid || "Not bound yet";
    adminNotes.value = "";
    customDateGroup.classList.add("hidden");
    planSelect.value = currentPlan && currentPlan !== "none" ? currentPlan : "lifetime";
    approveModal.classList.remove("hidden");
    refreshIcons();
}

function closeApproveModal() {
    approveModal.classList.add("hidden");
    targetUserIdToApprove = null;
}

async function resetUserHwid(userId, email) {
    if (!confirm(`Are you sure you want to unbind the device Hardware ID for ${email}?\n\nThis will allow the user to log in and bind a new PC.`)) {
        return;
    }
    try {
        await apiRequest(`/api/admin/users/${userId}/reset-hwid`, "POST");
        showToast(`Hardware ID reset for ${email}`, "success");
        loadDashboardData();
    } catch (err) {
        alert("Error: " + err.message);
    }
}

async function setUserStatus(userId, newStatus) {
    try {
        await apiRequest(`/api/admin/users/${userId}/status`, "POST", { status: newStatus });
        showToast(`Status updated to ${newStatus}`, "success");
        loadDashboardData();
    } catch (err) {
        alert("Error: " + err.message);
    }
}

async function deleteUser(userId, email) {
    if (!confirm(`Permanently delete account for ${email}? This action cannot be undone.`)) {
        return;
    }
    try {
        await apiRequest(`/api/admin/users/${userId}`, "DELETE");
        showToast(`User ${email} deleted`, "success");
        loadDashboardData();
    } catch (err) {
        alert("Error: " + err.message);
    }
}

function showToast(msg, type = "info") {
    let container = document.getElementById("toastNotification");
    if (!container) return;
    container.textContent = msg;
    container.className = `toast toast-${type}`;
    container.classList.remove("hidden");
    setTimeout(() => {
        container.classList.add("hidden");
    }, 3500);
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
