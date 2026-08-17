// Super Admin SaaS Dashboard Frontend Controller
let currentAdminToken = localStorage.getItem("dola_admin_token") || null;
let currentUsers = [];
let activeFilter = "all";
let targetUserIdToApprove = null;

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
const confirmApproveBtn = document.getElementById("confirmApproveBtn");
const customDateGroup = document.getElementById("customDateGroup");
const customExpiryDate = document.getElementById("customExpiryDate");
const adminNote = document.getElementById("adminNote");

// Initial Startup
document.addEventListener("DOMContentLoaded", () => {
    if (currentAdminToken) {
        showDashboard();
    } else {
        showLogin();
    }
    setupEventListeners();
});

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
    document.querySelectorAll(".filter-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            activeFilter = btn.dataset.status;
            renderUsers();
        });
    });

    // Radio button changes for custom date toggle
    document.querySelectorAll("input[name='planDuration']").forEach(radio => {
        radio.addEventListener("change", (e) => {
            if (e.target.value === "custom") {
                customDateGroup.classList.remove("hidden");
            } else {
                customDateGroup.classList.add("hidden");
            }
        });
    });

    // Confirm Approval in Modal
    confirmApproveBtn.addEventListener("click", async () => {
        if (!targetUserIdToApprove) return;
        
        const selectedPlan = document.querySelector("input[name='planDuration']:checked").value;
        let customDateVal = null;
        if (selectedPlan === "custom") {
            const rawVal = customExpiryDate.value;
            if (!rawVal) {
                alert("Please select a valid custom expiration date.");
                return;
            }
            customDateVal = new Date(rawVal).toISOString();
        }

        try {
            confirmApproveBtn.disabled = true;
            const res = await apiRequest(`/api/admin/users/${targetUserIdToApprove}/approve`, "POST", {
                plan_type: selectedPlan,
                custom_date: customDateVal,
                notes: adminNote.value.trim() || null
            });
            
            showToast(`User approved with ${formatPlanName(selectedPlan)}!`, "success");
            closeApproveModal();
            loadDashboardData();
        } catch (err) {
            alert("Error approving user: " + err.message);
        } finally {
            confirmApproveBtn.disabled = false;
        }
    });
}

function showLogin() {
    loginSection.classList.remove("hidden");
    dashboardSection.classList.add("hidden");
}

function showDashboard() {
    loginSection.classList.add("hidden");
    dashboardSection.classList.remove("hidden");
    loadDashboardData();
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
        const [stats, usersData] = await Promise.all([
            apiRequest("/api/admin/stats"),
            apiRequest("/api/admin/users")
        ]);
        
        // Update Stats
        document.getElementById("statTotal").textContent = stats.total;
        document.getElementById("statPending").textContent = stats.pending;
        document.getElementById("statActive").textContent = stats.active;
        document.getElementById("statExpired").textContent = stats.expired + stats.suspended;
        
        document.getElementById("countAll").textContent = stats.total;
        document.getElementById("countPending").textContent = stats.pending;

        currentUsers = usersData.users || [];
        renderUsers();
    } catch (err) {
        console.error(err);
    }
}

function renderUsers() {
    const searchTerm = searchInput.value.toLowerCase().trim();
    
    const filtered = currentUsers.filter(user => {
        // Status Filter
        if (activeFilter !== "all" && user.status !== activeFilter) {
            return false;
        }
        // Search Filter
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
                <td colspan="7" class="empty-state" style="text-align:center; padding: 40px; color: var(--text-muted);">
                    No users found matching your criteria.
                </td>
            </tr>
        `;
        return;
    }

    userTableBody.innerHTML = filtered.map(user => {
        const statusBadge = getStatusBadge(user.status);
        const planName = formatPlanName(user.plan_type);
        const expiryFormatted = formatExpiry(user.expires_at, user.plan_type);
        const hwidCell = formatHwid(user.hwid);
        const registeredDate = user.created_at ? new Date(user.created_at).toLocaleDateString() : "-";

        return `
            <tr>
                <td>
                    <div class="user-name-col">${escapeHtml(user.full_name || 'Anonymous')}</div>
                    <div class="user-email-sub">${escapeHtml(user.email)}</div>
                </td>
                <td>${statusBadge}</td>
                <td><strong>${planName}</strong></td>
                <td>${expiryFormatted}</td>
                <td>${hwidCell}</td>
                <td style="color: var(--text-muted); font-size: 13px;">${registeredDate}</td>
                <td class="text-right">
                    <div class="action-group">
                        <button class="btn btn-emerald btn-xs" onclick="openApproveModal(${user.id}, '${escapeHtml(user.email)}')">
                            ${user.status === 'active' ? '⚡ Extend / Change' : '✓ Approve'}
                        </button>
                        ${user.hwid ? `
                            <button class="btn btn-outline btn-xs" title="Unbind PC hardware ID so user can switch device" onclick="resetUserHwid(${user.id}, '${escapeHtml(user.email)}')">
                                🔓 Reset HWID
                            </button>
                        ` : ''}
                        ${user.status === 'active' ? `
                            <button class="btn btn-outline btn-xs text-rose" onclick="setUserStatus(${user.id}, 'suspended')">
                                Suspend
                            </button>
                        ` : user.status === 'suspended' ? `
                            <button class="btn btn-outline btn-xs text-emerald" onclick="setUserStatus(${user.id}, 'active')">
                                Reactivate
                            </button>
                        ` : ''}
                        <button class="btn btn-outline btn-xs" title="Delete User" style="color: #ef4444;" onclick="deleteUser(${user.id}, '${escapeHtml(user.email)}')">
                            🗑️
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}

function getStatusBadge(status) {
    switch (status) {
        case "pending":
            return `<span class="badge badge-pending">⏳ Pending</span>`;
        case "active":
            return `<span class="badge badge-active">🟢 Active</span>`;
        case "expired":
            return `<span class="badge badge-expired">🛑 Expired</span>`;
        case "suspended":
            return `<span class="badge badge-suspended">⏸️ Suspended</span>`;
        default:
            return `<span class="badge">${status}</span>`;
    }
}

function formatPlanName(plan) {
    switch (plan) {
        case "7_days": return "7 Days Trial";
        case "1_month": return "1 Month";
        case "1_year": return "1 Year";
        case "lifetime": return "👑 Lifetime";
        case "custom": return "Custom Plan";
        default: return "None";
    }
}

function formatExpiry(expires_at, plan_type) {
    if (plan_type === "lifetime") {
        return `<span class="text-emerald" style="font-weight:600;">👑 Never (Lifetime)</span>`;
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
        return `<span class="text-amber"><strong>${diffDays} days left</strong> (${expDate.toLocaleDateString()})</span>`;
    } else {
        return `<span>${diffDays} days left (${expDate.toLocaleDateString()})</span>`;
    }
}

function formatHwid(hwid) {
    if (!hwid) {
        return `<span class="hwid-unbound">Not Bound Yet</span>`;
    }
    return `<span class="hwid-badge" title="${escapeHtml(hwid)}">🔒 ${escapeHtml(hwid)}</span>`;
}

function openApproveModal(userId, email) {
    targetUserIdToApprove = userId;
    modalUserEmail.textContent = email;
    adminNote.value = "";
    customDateGroup.classList.add("hidden");
    document.querySelector("input[name='planDuration'][value='1_month']").checked = true;
    approveModal.classList.remove("hidden");
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
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
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
