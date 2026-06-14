document.addEventListener("DOMContentLoaded", () => {
    // Navigation
    const navLinks = document.querySelectorAll(".nav-links li");
    const views = document.querySelectorAll(".view");

    navLinks.forEach(link => {
        link.addEventListener("click", () => {
            navLinks.forEach(n => n.classList.remove("active"));
            link.classList.add("active");
            
            const targetId = link.getAttribute("data-target");
            views.forEach(v => v.classList.remove("active"));
            document.getElementById(targetId).classList.add("active");
            
            if (targetId === "dashboard") {
                loadDashboardData();
            } else if (targetId === "schedule") {
                initScheduleView();
            } else if (targetId === "overtime") {
                loadVaultData();
            }
        });
    });

    // Sidebar Excel Import
    document.getElementById("btn-sidebar-import").addEventListener("click", async () => {
        if (!window.pywebview) return;
        const userId = userSelect.value;
        if (!userId) {
            showToast("사용자를 먼저 선택해주세요.", "warning");
            return;
        }

        if (confirm("엑셀 데이터를 불러오시겠습니까?\n기존 데이터가 있는 날짜는 덮어씌워집니다.\n(양식이 궁금하시다면 '아니오'를 누른 후 템플릿을 생성하세요.)")) {
            try {
                const res = await window.pywebview.api.import_excel(parseInt(userId));
                if (res.status === "success") {
                    showToast("데이터를 성공적으로 불러왔습니다.", "success");
                    reloadAllData();
                } else {
                    showToast("불러오기 실패: " + res.message, "error");
                }
            } catch (e) {
                showToast("오류 발생", "error");
            }
        } else {
            // Offer to create template
            if (confirm("엑셀 불러오기용 양식(템플릿)을 만드시겠습니까?")) {
                const savePath = await window.pywebview.api.save_file_dialog("Import_Template.xlsx");
                if (savePath) {
                    const res = await window.pywebview.api.generate_template(savePath);
                    if (res.status === "success") {
                        showToast("템플릿이 저장되었습니다.", "success");
                    }
                }
            }
        }
    });

    // User Management
    const userSelect = document.getElementById("user-select");
    const btnAddUser = document.getElementById("btn-add-user");
    
    async function loadUsers() {
        if (!window.pywebview) return;
        try {
            const users = await window.pywebview.api.get_users();
            userSelect.innerHTML = '';
            if (users.length === 0) {
                userSelect.innerHTML = '<option value="">사용자 없음</option>';
            } else {
                const exportSelect = document.getElementById('export-user-select');
                if (exportSelect) exportSelect.innerHTML = '<option value="all">전체 (사용자별 시트 생성)</option>';
                users.forEach(u => {
                    const opt = document.createElement('option');
                    opt.value = u.id;
                    opt.innerText = u.name;
                    userSelect.appendChild(opt);
                    
                    if (exportSelect) {
                        const opt2 = document.createElement('option');
                        opt2.value = u.id;
                        opt2.innerText = u.name;
                        exportSelect.appendChild(opt2);
                    }
                });
            }
        } catch(e) {
            console.error("Failed to load users", e);
        }
    }
    
    const addUserModal = document.getElementById("add-user-modal");
    const addUserNameInput = document.getElementById("add-user-name");
    const btnAddUserCancel = document.getElementById("btn-add-user-cancel");
    const btnAddUserConfirm = document.getElementById("btn-add-user-confirm");
    const addUserTitle = document.getElementById("add-user-title");
    const addUserDesc = document.getElementById("add-user-desc");

    function openAddUserModal(title, desc) {
        addUserTitle.innerText = title || "사용자 추가";
        addUserDesc.innerText = desc || "등록할 사용자 이름을 입력하세요.";
        addUserNameInput.value = "";
        addUserModal.style.display = "flex";
        addUserNameInput.focus();
    }

    function closeAddUserModal() {
        addUserModal.style.display = "none";
    }

    btnAddUserCancel.addEventListener("click", closeAddUserModal);

    btnAddUserConfirm.addEventListener("click", async () => {
        const name = addUserNameInput.value;
        if (name && name.trim()) {
            try {
                const res = await window.pywebview.api.add_user(name.trim());
                if (res.status === 'success') {
                    showToast("사용자가 추가되었습니다.", "success");
                    await loadUsers();
                    userSelect.value = res.user_id;
                    reloadAllData();
                    closeAddUserModal();
                } else {
                    showToast("오류: " + res.message, "error");
                }
            } catch(e) {}
        }
    });

    btnAddUser.addEventListener("click", () => {
        openAddUserModal("사용자 추가", "추가할 사용자 이름을 입력하세요:");
    });
    
    // Delete User
    document.getElementById("btn-delete-user").addEventListener("click", async () => {
        if (!window.pywebview) return;
        const userId = userSelect.value;
        if (!userId) {
            showToast("삭제할 사용자를 선택해주세요.", "warning");
            return;
        }
        const userName = userSelect.options[userSelect.selectedIndex].text;
        if (!confirm(`정말로 사용자 '${userName}'을(를) 삭제하시겠습니까? 이 작업은 되돌릴 수 없으며 관련된 모든 근무 기록이 삭제됩니다.`)) {
            return;
        }
        try {
            const res = await window.pywebview.api.delete_user(parseInt(userId));
            if (res.status === "success") {
                showToast("사용자가 삭제되었습니다.", "success");
                await loadUsers();
            } else {
                showToast("삭제 실패: " + res.message, "error");
            }
        } catch(e) {
            showToast("오류 발생", "error");
            console.error(e);
        }
    });

    userSelect.addEventListener("change", reloadAllData);
    
    function reloadAllData() {
        loadDashboardData();
        loadVaultData();
        if (document.getElementById("schedule").classList.contains("active")) {
            loadScheduleData();
        }
    }

    // Time Entry Defaults & Logic
    const entryDate = document.getElementById("entry-date");
    const entryType = document.getElementById("entry-type");
    const clockIn = document.getElementById("clock-in");
    const clockOut = document.getElementById("clock-out");
    const nonWork = document.getElementById("non-work");
    const btnMinus30 = document.getElementById("btn-minus-30");
    const btnPlus30 = document.getElementById("btn-plus-30");
    const timeInputsContainer = document.getElementById("time-inputs-container");

    // Default to today
    const today = new Date();
    entryDate.value = today.toISOString().split('T')[0];

    function applyDefaults() {
        const type = entryType.value;
        if (type === "normal") {
            clockIn.value = "08:30";
            clockOut.value = "17:30";
            timeInputsContainer.style.display = "grid";
            nonWork.value = 0;
        } else if (type === "morning_half") {
            clockIn.value = "08:30";
            clockOut.value = "12:30";
            timeInputsContainer.style.display = "grid";
            nonWork.value = 0;
        } else if (type === "afternoon_half") {
            clockIn.value = "13:30";
            clockOut.value = "17:30";
            timeInputsContainer.style.display = "grid";
            nonWork.value = 0;
        }
        
        if (type === "holiday" || type === "annual_leave" || type === "public_leave" || type === "sick_leave" || type === "replacement_leave" || type === "public_leave_half") {
            timeInputsContainer.style.display = "none";
        } else {
            timeInputsContainer.style.display = "grid";
        }

        // Toggle holiday description field
        const holidayGroup = document.getElementById("holiday-desc-group");
        if (type === "holiday" || type === "public_leave_half") {
            holidayGroup.style.display = "block";
        } else {
            holidayGroup.style.display = "none";
            document.getElementById("holiday-desc").value = "";
        }
    }

    entryType.addEventListener("change", applyDefaults);
    entryDate.addEventListener("change", applyDefaults);

    btnMinus30.addEventListener("click", () => {
        let val = parseInt(nonWork.value) || 0;
        if (val >= 30) nonWork.value = val - 30;
    });

    btnPlus30.addEventListener("click", () => {
        let val = parseInt(nonWork.value) || 0;
        nonWork.value = val + 30;
    });
    
    // Overtime Buttons
    document.getElementById("btn-ot-4h").addEventListener("click", () => {
        document.getElementById("overtime-used").value = 4;
    });
    document.getElementById("btn-ot-8h").addEventListener("click", () => {
        document.getElementById("overtime-used").value = 8;
    });

    document.getElementById("btn-save-log").addEventListener("click", async () => {
        if (!window.pywebview) {
            showToast("앱 초기화 중입니다. 잠시 후 다시 시도해주세요.", "warning");
            return;
        }
        
        const userId = userSelect.value;
        if (!userId) {
            showToast("사용자를 먼저 추가/선택해주세요.", "warning");
            return;
        }
        
        const data = {
            user_id: parseInt(userId),
            date: entryDate.value,
            type: entryType.value,
            clock_in: clockIn.value,
            clock_out: clockOut.value,
            non_work_time: nonWork.value,
            overtime_used: (parseInt(document.getElementById("overtime-used").value) || 0) * 60,
            description: document.getElementById("holiday-desc").value || ""
        };

        try {
            const res = await window.pywebview.api.save_log(data);
            if (res.status === "success") {
                showToast("저장되었습니다.", "success");
                
                // Increment date to next working day
                const current = new Date(entryDate.value);
                current.setDate(current.getDate() + 1);
                while (current.getDay() === 0 || current.getDay() === 6) { // Skip Sat/Sun
                    current.setDate(current.getDate() + 1);
                }
                entryDate.value = current.toISOString().split('T')[0];
                applyDefaults();
                
                reloadAllData();
            }
        } catch (err) {
            showToast("저장 실패: " + (err.message || err), "error");
            console.error("Save error:", err);
        }
    });

    entryDate.addEventListener("change", () => {
        applyDefaults();
    });

    // Dashboard Data
    const dashWeek = document.getElementById("dash-week");
    
    // Set current week for dashboard (e.g. "2026-W17")
    const getWeekString = (d) => {
        const date = new Date(d.getTime());
        date.setHours(0, 0, 0, 0);
        date.setDate(date.getDate() + 3 - (date.getDay() + 6) % 7);
        const week1 = new Date(date.getFullYear(), 0, 4);
        const weekNumber = 1 + Math.round(((date.getTime() - week1.getTime()) / 86400000 - 3 + (week1.getDay() + 6) % 7) / 7);
        return `${date.getFullYear()}-W${weekNumber.toString().padStart(2, '0')}`;
    };
    
    dashWeek.value = getWeekString(today);
    
    function updateWeekDisplay() {
        const weekVal = dashWeek.value;
        if (weekVal) {
            const [year, week] = weekVal.split('-W');
            document.getElementById("dash-week-text").innerText = `${year}년, ${week}주`;
        }
    }
    updateWeekDisplay();

    dashWeek.addEventListener("change", () => {
        updateWeekDisplay();
        loadDashboardData();
    });

    async function loadDashboardData() {
        if (!window.pywebview) return;
        
        const weekVal = dashWeek.value; // "YYYY-Www"
        if(!weekVal) return;
        const [year, week] = weekVal.split('-W');
        const simpleDate = new Date(year, 0, 1 + (week - 1) * 7);
        const dateStr = simpleDate.toISOString().split('T')[0];
        
        const userId = userSelect.value;
        if (!userId) return;

        try {
            const res = await window.pywebview.api.get_weekly_summary(parseInt(userId), dateStr);
            const totalMins = res.total_minutes;
            const hours = Math.floor(totalMins / 60);
            const mins = totalMins % 60;
            
            document.getElementById("weekly-hours").innerText = `${hours}h ${mins}m`;
            
            // Total Overtime for that week
            // Note: get_weekly_summary should ideally return overtime too, but for now we focus on total mins
            
            const progress = document.getElementById("weekly-progress");
            const maxMins = 52 * 60;
            let percent = (totalMins / maxMins) * 100;
            if (percent > 100) percent = 100;
            progress.style.width = `${percent}%`;
            
            if (hours >= 46 && hours < 52) {
                progress.style.background = "linear-gradient(90deg, #f59e0b, #ef4444)";
                showToast("경고: 주 46시간을 초과했습니다.", "warning");
            } else if (hours >= 52) {
                progress.style.background = "#ef4444";
                showToast("주 52시간 제한에 도달했습니다!", "error");
            } else {
                progress.style.background = "linear-gradient(90deg, #3b82f6, #8b5cf6)";
            }

            // Total Remaining Overtime (Monthly Summary)
            const stats = await window.pywebview.api.get_monthly_summary(parseInt(userId), dateStr.substring(0,7));
            document.getElementById("total-overtime").innerText = formatHm(stats.total_remaining);
            
            // Load Chart Data (Commented out in UI, but safe to keep logic or ignore)
            // const yearlySummary = await window.pywebview.api.get_yearly_summary(parseInt(userId));
            // renderDonutChart(yearlySummary);
            
            // Populate Weekly Schedule Table in Dashboard
            const day = simpleDate.getDay();
            const diff = simpleDate.getDate() - day + (day === 0 ? -6 : 1);
            const startOfWeek = new Date(new Date(simpleDate).setDate(diff));
            const endOfWeek = new Date(startOfWeek);
            endOfWeek.setDate(startOfWeek.getDate() + 6);
            
            const startDateStr = startOfWeek.toISOString().split('T')[0];
            const endDateStr = endOfWeek.toISOString().split('T')[0];
            
            const weeklyBody = document.getElementById("schedule-weekly-body");
            if (weeklyBody) {
                const logs = await window.pywebview.api.get_logs(parseInt(userId), startDateStr, endDateStr);
                weeklyBody.innerHTML = "";
                const days = ["일", "월", "화", "수", "목", "금", "토"];
                const typeNames = {
                    "normal": "정상 근무", 
                    "morning_half": "오전 반차", 
                    "afternoon_half": "오후 반차", 
                    "holiday": "공휴일 / 특별휴가",
                    "annual_leave": "연차",
                    "public_leave": "공가",
                    "public_leave_half": "반공가 + 반차",
                    "sick_leave": "병가",
                    "replacement_leave": "휴무"
                };
                logs.forEach(log => {
                    const dateObj = new Date(log.date);
                    let displayType = typeNames[log.type] || log.type;
                    if (log.type === "holiday" && log.description) {
                        displayType = `공휴일 - ${log.description}`;
                    }
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td>${log.date}</td>
                        <td>${days[dateObj.getDay()]}</td>
                        <td>${displayType}</td>
                        <td>${log.clock_in}</td>
                        <td>${log.clock_out}</td>
                        <td>${formatHm(log.work_time)}</td>
                        <td>${log.description || ''}</td>
                    `;
                    weeklyBody.appendChild(tr);
                });
                if (logs.length === 0) {
                    weeklyBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 2rem;">기록이 없습니다.</td></tr>';
                }
            }
            
        } catch(e) {
            console.error(e);
        }
    }

    function renderDonutChart(data) {
        const container = document.getElementById("dashboard-chart-container");
        const legend = document.getElementById("chart-legend");
        container.innerHTML = "";
        legend.innerHTML = "";

        if (!data || data.length === 0) {
            container.innerHTML = "<p style='font-size:0.8rem; color:#aaa;'>데이터 없음</p>";
            return;
        }

        const sortedData = [...data].sort((a, b) => b.total - a.total).slice(0, 8);
        const totalSum = sortedData.reduce((acc, curr) => acc + curr.total, 0);
        
        if (totalSum === 0) {
            container.innerHTML = "<p style='font-size:0.8rem; color:#aaa;'>연장근무 없음</p>";
            return;
        }

        const colors = ["#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#ef4444", "#6366f1", "#06b6d4"];
        
        const svgSize = 200;
        const center = svgSize / 2;
        const radius = 70;
        const circumference = 2 * Math.PI * radius;
        
        let cumulativePercent = 0;
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("width", svgSize);
        svg.setAttribute("height", svgSize);
        
        sortedData.forEach((item, index) => {
            const percent = (item.total / totalSum);
            const color = colors[index % colors.length];
            
            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.setAttribute("cx", center);
            circle.setAttribute("cy", center);
            circle.setAttribute("r", radius);
            circle.classList.add("chart-segment");
            circle.style.stroke = color;
            
            const offset = circumference * cumulativePercent;
            circle.style.strokeDasharray = `${circumference * percent} ${circumference}`;
            circle.style.strokeDashoffset = -offset;
            
            svg.appendChild(circle);
            
            const legendItem = document.createElement("div");
            legendItem.className = "legend-item";
            legendItem.innerHTML = `
                <div class="legend-color" style="background: ${color}"></div>
                <span>${item.month}: ${formatHm(item.total)}</span>
            `;
            legend.appendChild(legendItem);
            
            cumulativePercent += percent;
        });

        const text = document.createElement("div");
        text.style.position = "absolute";
        text.style.top = "50%";
        text.style.left = "50%";
        text.style.transform = "translate(-50%, -50%)";
        text.style.textAlign = "center";
        text.innerHTML = `<span style="font-size:0.7rem; color:#aaa;">연간 총계</span><br><span style="font-weight:bold; font-size:1rem;">${formatHm(totalSum)}</span>`;
        
        container.appendChild(svg);
        container.appendChild(text);
    }

    // Weekly Schedule Logic removed and merged into loadDashboardData

    // Schedule View Logic
    const scheduleMonth = document.getElementById("schedule-month");
    const scheduleBody = document.getElementById("schedule-body");

    function initScheduleView() {
        if (!scheduleMonth.value) {
            scheduleMonth.value = today.toISOString().substring(0, 7);
        }
        loadScheduleData();
    }

    scheduleMonth.addEventListener("change", loadScheduleData);

    function formatHm(mins) {
        if (!mins) return "0h 0m";
        return `${Math.floor(mins/60)}h ${mins%60}m`;
    }

    async function loadScheduleData() {
        if (!window.pywebview) return;
        
        const monthVal = scheduleMonth.value;
        if(!monthVal) return;
        const [year, month] = monthVal.split('-');
        const startStr = `${year}-${month}-01`;
        let nextMonth = new Date(year, month, 1);
        let lastDay = new Date(nextMonth.getTime() - 1);
        const endStr = lastDay.toISOString().split('T')[0];
        
        const userId = userSelect.value;
        if (!userId) {
            scheduleBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 2rem;">사용자를 선택해주세요.</td></tr>';
            return;
        }
        
        try {
            // Fetch stats
            const stats = await window.pywebview.api.get_monthly_summary(parseInt(userId), monthVal);
            document.getElementById("stat-earned").innerText = formatHm(stats.curr_earned);
            document.getElementById("stat-used").innerText = formatHm(stats.curr_used);
            document.getElementById("stat-carry").innerText = formatHm(stats.carry_over);
            document.getElementById("stat-total").innerText = formatHm(stats.total_remaining);
        
            // Fetch logs
            const logs = await window.pywebview.api.get_logs(parseInt(userId), startStr, endStr);
            scheduleBody.innerHTML = '';
            
            const typeNames = {
                "normal": "정상 근무", 
                "morning_half": "오전 반차", 
                "afternoon_half": "오후 반차", 
                "holiday": "공휴일 / 특별휴가",
                "annual_leave": "연차",
                "public_leave": "공가",
                "public_leave_half": "반공가 + 반차",
                "sick_leave": "병가",
                "replacement_leave": "휴무"
            };
            
            logs.forEach(log => {
                let displayType = typeNames[log.type] || log.type;
                if (log.type === "holiday" && log.description) {
                    displayType = `공휴일 - ${log.description}`;
                } else if (log.description) {
                    displayType = `${displayType} (${log.description})`;
                }
                
                const tr = document.createElement("tr");
                if (log.overtime_earned > 0) {
                    tr.classList.add("highlight-overtime");
                }
                
                let earnedText = log.overtime_earned ? (log.overtime_earned/60).toFixed(2) : '';
                let usedText = log.overtime_used ? (log.overtime_used/60).toFixed(2) : '';

                tr.innerHTML = `
                    <td>${log.date}</td>
                    <td>${displayType}</td>
                    <td>${log.clock_in}</td>
                    <td>${log.clock_out}</td>
                    <td>${formatHm(log.non_work_time)}</td>
                    <td>${formatHm(log.break_time)}</td>
                    <td>${formatHm(log.work_time)}</td>
                    <td style="color:var(--accent-color); font-weight:bold;">${earnedText}</td>
                    <td style="color:var(--warning); font-weight:bold;">${usedText}</td>
                `;
                scheduleBody.appendChild(tr);
            });
            
            if (logs.length === 0) {
                scheduleBody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding: 2rem;">기록이 없습니다.</td></tr>';
            }
        } catch(e) {
            console.error(e);
        }
    }

    // Export moved to header
    document.getElementById("btn-schedule-export").addEventListener("click", async () => {
        if (!window.pywebview) return;
        const userId = userSelect.value;
        if (!userId) {
            showToast("사용자를 먼저 선택해주세요.", "warning");
            return;
        }
        
        const month = scheduleMonth.value;
        try {
            const defaultFilename = await window.pywebview.api.get_suggested_filename(parseInt(userId), month);
            const savePath = await window.pywebview.api.save_file_dialog(defaultFilename);
            if (savePath) {
                const res = await window.pywebview.api.export_excel(parseInt(userId), month, savePath);
                if (res.status === "success") {
                    showToast("엑셀 파일이 저장되었습니다.", "success");
                } else {
                    showToast("내보내기 실패: " + res.message, "error");
                }
            }
        } catch(e) {}
    });

    // Vault (Renamed to Overtime Status in HTML)
    const vaultBody = document.getElementById("vault-body");
    async function loadVaultData() {
        if (!window.pywebview) return;
        const userId = userSelect.value;
        if (!userId) return;
        try {
            const vaults = await window.pywebview.api.get_vault_details(parseInt(userId));
            vaultBody.innerHTML = '';
            vaults.forEach(v => {
                const tr = document.createElement('tr');
                
                tr.innerHTML = `
                    <td>${v.date}</td>
                    <td style="color:var(--warning); font-weight:bold;">${v.used_minutes > 0 ? formatHm(v.used_minutes) : '-'}</td>
                    <td style="color:var(--accent-color); font-weight:bold;">${formatHm(v.remain_minutes)}</td>
                `;
                vaultBody.appendChild(tr);
            });
            if (vaults.length === 0) {
                vaultBody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding: 2rem;">내역이 없습니다.</td></tr>';
            }
        } catch(e) { console.error(e); }
    }

    // Modal
    window.openAdminModal = function(vaultId) {
        document.getElementById("modal-vault-id").value = vaultId;
        document.getElementById("admin-pw").value = '';
        document.getElementById("admin-modal").classList.add("show");
    };

    document.getElementById("btn-modal-cancel").addEventListener("click", () => {
        document.getElementById("admin-modal").classList.remove("show");
    });

    document.getElementById("btn-modal-confirm").addEventListener("click", async () => {
        const vaultId = document.getElementById("modal-vault-id").value;
        const pw = document.getElementById("admin-pw").value;
        if (!pw) return showToast("비밀번호를 입력하세요", "warning");
        
        try {
            const res = await window.pywebview.api.extend_overtime(vaultId, pw);
            if (res.status === "success") {
                showToast("유효기간이 연장되었습니다.", "success");
                document.getElementById("admin-modal").classList.remove("show");
                loadVaultData();
            } else {
                showToast(res.message, "error");
            }
        } catch(e) {
            showToast("오류 발생", "error");
        }
    });

    // Toast
    function showToast(message, type="success") {
        const toast = document.getElementById("toast");
        toast.className = "toast " + type;
        toast.innerText = message;
        toast.classList.add("show");
        setTimeout(() => {
            toast.classList.remove("show");
        }, 3000);
    }
    
    // Initial load when pywebview is ready
    window.addEventListener("pywebviewready", async function() {
        await loadUsers();
        
        // If no users exist, prompt to create one
        if (userSelect.options.length === 1 && !userSelect.value) {
            openAddUserModal("환영합니다!", "등록할 사용자 이름을 입력하세요:");
        }
        
        reloadAllData();
    });

    // Auto-fill logic
    document.getElementById("btn-autofill-exec").addEventListener("click", async () => {
        if (!window.pywebview) return;
        const userId = userSelect.value;
        const month = document.getElementById("autofill-month").value;
        if (!userId || !month) {
            showToast("사용자와 대상 월을 모두 선택해주세요.", "warning");
            return;
        }
        
        if (confirm("이전 일 중 기본 근무 시간이 비어 있는 곳에 기본 근무일을 채우시겠습니까?\n(주의: 공휴일, 특별휴가 등은 자동 채우기 후 별도로 수정해야 합니다)")) {
            try {
                const res = await window.pywebview.api.auto_fill_missing_days(parseInt(userId), month);
                if (res.status === "success") {
                    showToast(res.count + "개의 누락일자가 채워졌습니다.", "success");
                    reloadAllData();
                } else {
                    showToast("오류: " + res.message, "error");
                }
            } catch(e) {
                showToast("실행 중 오류 발생", "error");
            }
        }
    });

    // Yearly Export Logic
    const yearlyModal = document.getElementById("yearly-export-modal");
    document.getElementById("btn-yearly-export-modal").addEventListener("click", () => {
        document.getElementById("export-year").value = new Date().getFullYear();
        yearlyModal.style.display = "flex";
    });
    
    document.getElementById("btn-yearly-cancel").addEventListener("click", () => {
        yearlyModal.style.display = "none";
    });
    
    document.getElementById("btn-yearly-exec").addEventListener("click", async () => {
        if (!window.pywebview) return;
        const year = document.getElementById("export-year").value;
        const expUserEl = document.getElementById("export-user-select");
        const expUserId = expUserEl.value;
        let expUserName = expUserEl.options[expUserEl.selectedIndex].text.replace(' (사용자별 시트 생성)', '').trim();
        
        if (!year) {
            showToast("연도를 입력해주세요.", "warning");
            return;
        }
        
        yearlyModal.style.display = "none";
        try {
            const res = await window.pywebview.api.export_yearly_excel(year, expUserId, expUserName);
            if (res.status === "success") {
                showToast("연간 근무표 내보내기가 완료되었습니다.", "success");
            } else if (res.message !== "cancel") {
                showToast("오류: " + res.message, "error");
            }
        } catch(e) {
            showToast("내보내기 중 오류 발생", "error");
        }
    });
});
