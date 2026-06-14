import sys

with open('web/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update loadUsers
old_load = '''                users.forEach(u => {
                    const opt = document.createElement('option');
                    opt.value = u.id;
                    opt.innerText = u.name;
                    userSelect.appendChild(opt);
                });'''

new_load = '''                const exportSelect = document.getElementById('export-user-select');
                if (exportSelect) exportSelect.innerHTML = '<option value=\"all\">전체 (사용자별 시트 생성)</option>';
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
                });'''

content = content.replace(old_load, new_load)

# 2. Add event listeners at the end of app.js
new_listeners = '''
    // Auto-fill logic
    document.getElementById("btn-autofill-exec").addEventListener("click", async () => {
        if (!window.pywebview) return;
        const userId = userSelect.value;
        const month = document.getElementById("autofill-month").value;
        if (!userId || !month) {
            showToast("사용자와 대상 월을 모두 선택해주세요.", "warning");
            return;
        }
        
        if (confirm("이전 일 중 기본 근무 시간이 비어 있는 곳에 기본 근무일을 채우시겠습니까?\\n(주의: 공휴일, 특별휴가 등은 자동 채우기 후 별도로 수정해야 합니다)")) {
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
        const expUser = document.getElementById("export-user-select").value;
        
        if (!year) {
            showToast("연도를 입력해주세요.", "warning");
            return;
        }
        
        yearlyModal.style.display = "none";
        try {
            const res = await window.pywebview.api.export_yearly_excel(year, expUser);
            if (res.status === "success") {
                showToast("년간 근무표 내보내기가 완료되었습니다.", "success");
            } else if (res.message !== "cancel") {
                showToast("오류: " + res.message, "error");
            }
        } catch(e) {
            showToast("내보내기 중 오류 발생", "error");
        }
    });
});
'''

# Replace the last `});` with `new_listeners`
if content.endswith('});\n'):
    content = content[:-4] + new_listeners
elif content.endswith('});'):
    content = content[:-3] + new_listeners

with open('web/app.js', 'w', encoding='utf-8') as f:
    f.write(content)
