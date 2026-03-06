(function () {
    const dropzoneZip = document.getElementById('dropzoneZip');
    const dropzonePdf = document.getElementById('dropzonePdf');
    const fileInputZip = document.getElementById('fileInputZip');
    const fileInputPdf = document.getElementById('fileInputPdf');
    const zipFilename = document.getElementById('zipFilename');
    const pdfFilename = document.getElementById('pdfFilename');
    const uploadSection = document.getElementById('uploadSection');
    const dashboard = document.getElementById('dashboard');
    const loading = document.getElementById('loading');
    const errorEl = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');

    let weightChart = null;
    let nutritionChart = null;
    let exerciseChart = null;
    let selectedZip = null;
    let selectedPdf = null;
    let lastReportData = null;

    // Set default target date (90 days from today)
    (function setDefaultTargetDate() {
        const targetDateEl = document.getElementById('targetDate');
        if (targetDateEl && !targetDateEl.value) {
            const d = new Date();
            d.setDate(d.getDate() + 90);
            targetDateEl.value = d.toISOString().slice(0, 10);
        }
    })();

    // Prevent browser from opening files when dropped outside dropzone
    document.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
    });
    document.addEventListener('drop', (e) => {
        e.preventDefault();
    });

    function setupDropzone(el, type, onFile) {
        // Click is handled natively by <label> wrapping the file input
        el.addEventListener('dragenter', (e) => {
            e.preventDefault();
            e.stopPropagation();
            el.classList.add('dragover');
        });
        el.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.dataTransfer.dropEffect = 'copy';
            el.classList.add('dragover');
        });
        el.addEventListener('dragleave', (e) => {
            if (!el.contains(e.relatedTarget)) el.classList.remove('dragover');
        });
        el.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            el.classList.remove('dragover');
            const file = (e.dataTransfer.files && e.dataTransfer.files[0]) || null;
            if (file) onFile(file);
        });
    }

    setupDropzone(dropzoneZip, 'zip', (file) => {
        if (!file.name.toLowerCase().endsWith('.zip')) {
            showError('Selecione um arquivo .zip');
            return;
        }
        selectedZip = file;
        zipFilename.textContent = file.name;
        dropzoneZip.classList.add('has-file');
    });

    setupDropzone(dropzonePdf, 'pdf', (file) => {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            showError('Selecione um arquivo .pdf');
            return;
        }
        selectedPdf = file;
        pdfFilename.textContent = file.name;
        dropzonePdf.classList.add('has-file');
    });

    fileInputZip.addEventListener('change', (e) => {
        const file = e.target.files && e.target.files[0];
        if (file) {
            selectedZip = file;
            zipFilename.textContent = file.name;
            dropzoneZip.classList.add('has-file');
        }
    });

    fileInputPdf.addEventListener('change', (e) => {
        const file = e.target.files && e.target.files[0];
        if (file) {
            selectedPdf = file;
            pdfFilename.textContent = file.name;
            dropzonePdf.classList.add('has-file');
        }
    });

    document.getElementById('btnCalculate').addEventListener('click', () => {
        // Use files from inputs directly (robust when selected via label)
        const zipFile = selectedZip || (fileInputZip.files && fileInputZip.files[0]);
        const pdfFile = selectedPdf || (fileInputPdf.files && fileInputPdf.files[0]);
        if (!zipFile) {
            showError('Selecione o arquivo ZIP primeiro.');
            return;
        }
        if (!pdfFile) {
            showError('Selecione o arquivo PDF primeiro.');
            return;
        }
        processFiles(zipFile, pdfFile);
    });

    document.getElementById('exportJsonBtn').addEventListener('click', () => {
        if (!lastReportData) {
            showError('Nenhum relatório para exportar. Calcule primeiro.');
            return;
        }
        const jsonStr = JSON.stringify(lastReportData, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'cutting_report.json';
        a.click();
        URL.revokeObjectURL(url);
    });

    document.getElementById('btnNewUpload').addEventListener('click', () => {
        dashboard.classList.add('hidden');
        uploadSection.classList.remove('hidden');
        selectedZip = null;
        selectedPdf = null;
        lastReportData = null;
        zipFilename.textContent = 'Arraste ou clique';
        pdfFilename.textContent = 'Arraste ou clique';
        dropzoneZip.classList.remove('has-file');
        dropzonePdf.classList.remove('has-file');
        fileInputZip.value = '';
        fileInputPdf.value = '';
        // Reset form (keep target date default)
        const d = new Date();
        d.setDate(d.getDate() + 90);
        const targetEl = document.getElementById('targetDate');
        if (targetEl) targetEl.value = d.toISOString().slice(0, 10);
        const nameEl = document.getElementById('userName');
        if (nameEl) nameEl.value = '';
        const sexEl = document.getElementById('userSex');
        if (sexEl) sexEl.value = '';
        const heightEl = document.getElementById('userHeight');
        if (heightEl) heightEl.value = '';
        const ageEl = document.getElementById('userAge');
        if (ageEl) ageEl.value = '';
    });

    function showError(msg) {
        errorMessage.textContent = msg;
        errorEl.classList.remove('hidden');
        setTimeout(() => errorEl.classList.add('hidden'), 5000);
    }

    function getUserParams() {
        const targetDate = document.getElementById('targetDate')?.value || '';
        const name = document.getElementById('userName')?.value?.trim() || null;
        const sex = document.getElementById('userSex')?.value || null;
        const heightCm = document.getElementById('userHeight')?.value;
        const age = document.getElementById('userAge')?.value;
        const weightKg = document.getElementById('userWeight')?.value;
        const calorieMin = document.getElementById('calorieMin')?.value;
        const calorieMax = document.getElementById('calorieMax')?.value;
        const proteinG = document.getElementById('proteinG')?.value;
        const fiberG = document.getElementById('fiberG')?.value;
        return {
            target_date: targetDate || null,
            name: name,
            sex: sex,
            height_cm: heightCm ? parseInt(heightCm, 10) : null,
            age: age ? parseInt(age, 10) : null,
            weight_kg: weightKg ? parseFloat(weightKg) : null,
            calorie_min: calorieMin ? parseInt(calorieMin, 10) : null,
            calorie_max: calorieMax ? parseInt(calorieMax, 10) : null,
            protein_g: proteinG ? parseInt(proteinG, 10) : null,
            fiber_g: fiberG ? parseInt(fiberG, 10) : null,
        };
    }

    async function processFiles(zipFile, pdfFile) {
        loading.classList.remove('hidden');
        errorEl.classList.add('hidden');

        const userParams = getUserParams();
        if (!userParams.target_date) {
            showError('Defina a data alvo.');
            loading.classList.add('hidden');
            return;
        }

        const formData = new FormData();
        formData.append('zip_file', zipFile);
        formData.append('pdf_file', pdfFile);
        formData.append('target_date', userParams.target_date);
        if (userParams.name) formData.append('name', userParams.name);
        if (userParams.sex) formData.append('sex', userParams.sex);
        if (userParams.height_cm != null) formData.append('height_cm', userParams.height_cm);
        if (userParams.age != null) formData.append('age', userParams.age);
        if (userParams.weight_kg != null) formData.append('weight_kg', userParams.weight_kg);
        if (userParams.calorie_min != null) formData.append('calorie_min', userParams.calorie_min);
        if (userParams.calorie_max != null) formData.append('calorie_max', userParams.calorie_max);
        if (userParams.protein_g != null) formData.append('protein_g', userParams.protein_g);
        if (userParams.fiber_g != null) formData.append('fiber_g', userParams.fiber_g);

        try {
            const res = await fetch('/api/process', {
                method: 'POST',
                body: formData,
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.error || 'Erro ao processar arquivos');
            }

            document.getElementById('fileStatus').textContent =
                `Processado: ${zipFile.name} + ${pdfFile.name}`;

            renderDashboard(data);
            uploadSection.classList.add('hidden');
            dashboard.classList.remove('hidden');
        } catch (err) {
            showError(err.message);
        } finally {
            loading.classList.add('hidden');
        }
    }

    function renderDashboard(data) {
        lastReportData = data;

        // User info summary (name, sex, height, age, target date)
        const user = data.user || {};
        const targetDate = data.target_date;
        const userParts = [];
        if (user.name) userParts.push(user.name);
        if (user.sex) userParts.push(user.sex === 'M' ? 'Masculino' : 'Feminino');
        if (user.age != null) userParts.push(user.age + ' anos');
        if (user.height_cm != null) userParts.push(user.height_cm + ' cm');
        if (targetDate) userParts.push('Data alvo: ' + targetDate);
        const userSummaryEl = document.getElementById('userInfoSummary');
        if (userSummaryEl) {
            userSummaryEl.textContent = userParts.length ? userParts.join(' · ') : '';
            userSummaryEl.style.display = userParts.length ? '' : 'none';
        }

        // Summary cards (quick overview)
        const pdfV2Body = (data.pdf_report_v2 || {}).body || {};
        const fatPct = pdfV2Body.derived_fat_mass_pct ?? (data.weight || {}).body_fat?.average_pct;
        document.getElementById('summaryFat').textContent = fatPct != null ? fatPct + '%' : '--';

        const avgCal = (data.nutrition || {}).avg_calories;
        document.getElementById('summaryCalories').textContent = avgCal != null ? avgCal + ' kcal' : '--';

        const n = data.nutrition || {};
        const daysTarget = n.days_1800_to_1950 ?? 0;
        const daysLogged = n.days_logged ?? 0;
        const insightsText = daysLogged > 0 ? daysTarget + ' dias na meta' : '--';
        const insightsEl = document.getElementById('summaryInsights');
        insightsEl.textContent = insightsText;
        insightsEl.className = 'summary-card-value' + (daysTarget >= daysLogged * 0.5 && daysLogged > 0 ? ' alert-ok' : '');

        const alerts = data.alerts || {};
        const criticalCount = (alerts.critical || []).length;
        const warningCount = (alerts.warning || []).length;
        const infoCount = (alerts.info || []).length;
        const totalAlerts = criticalCount + warningCount + infoCount;
        const alertsParts = [];
        if (criticalCount) alertsParts.push(criticalCount + ' crítico(s)');
        if (warningCount) alertsParts.push(warningCount + ' aviso(s)');
        if (infoCount) alertsParts.push(infoCount + ' info');
        const alertsEl = document.getElementById('summaryAlerts');
        alertsEl.textContent = totalAlerts === 0 ? 'Nenhum' : alertsParts.join(', ');
        alertsEl.className = 'summary-card-value' + (criticalCount > 0 ? ' alert-critical' : warningCount > 0 ? ' alert-warning' : '');

        // Weight
        const w = data.weight || {};
        document.getElementById('latestWeight').textContent = w.latest_weight_kg ?? '--';
        document.getElementById('ma5').textContent = w.latest_ma5_kg ?? '--';
        document.getElementById('ma7').textContent = w.latest_ma7_kg ?? '--';

        const trendEl = document.getElementById('ma7Trend');
        const change = w.ma7_change_kg;
        if (change != null) {
            const span = trendEl.querySelector('.stat-value');
            span.textContent = (change >= 0 ? '+' : '') + change + ' kg';
            span.className = 'stat-value ' + (change > 0 ? 'positive' : change < 0 ? 'negative' : '');
        }

        const totalLossEl = document.getElementById('totalLoss');
        const totalLoss = w.total_loss_kg;
        if (totalLoss != null) {
            totalLossEl.textContent = (totalLoss >= 0 ? '+' : '') + totalLoss + ' kg';
            totalLossEl.className = 'stat-value ' + (totalLoss < 0 ? 'negative' : totalLoss > 0 ? 'positive' : '');
        } else {
            totalLossEl.textContent = '--';
        }

        const lossRateEl = document.getElementById('lossRate');
        const lossRate = w.loss_rate_kg_per_week;
        if (lossRate != null) {
            lossRateEl.textContent = (lossRate >= 0 ? '+' : '') + lossRate + ' kg/sem';
            lossRateEl.className = 'stat-value ' + (lossRate < 0 ? 'negative' : lossRate > 0 ? 'positive' : '');
        } else {
            lossRateEl.textContent = '--';
        }

        const bodyFatStat = document.getElementById('bodyFatStat');
        const latestBodyFatEl = document.getElementById('latestBodyFat');
        const bodyFat = w.body_fat || {};
        if (bodyFat.average_pct != null) {
            latestBodyFatEl.textContent = bodyFat.average_pct + '%';
            bodyFatStat.style.display = '';
        } else {
            bodyFatStat.style.display = 'none';
        }

        const fatMassTrendStat = document.getElementById('fatMassTrendStat');
        const leanMassTrendStat = document.getElementById('leanMassTrendStat');
        const fatMassTrendEl = document.getElementById('fatMassTrend');
        const leanMassTrendEl = document.getElementById('leanMassTrend');
        if (w.pdf_fat_mass_trend_kg != null) {
            const val = w.pdf_fat_mass_trend_kg;
            fatMassTrendEl.textContent = (val >= 0 ? '+' : '') + val + ' kg';
            fatMassTrendEl.className = 'stat-value ' + (val < 0 ? 'negative' : val > 0 ? 'positive' : '');
            fatMassTrendStat.style.display = '';
        } else {
            fatMassTrendStat.style.display = 'none';
        }
        if (w.pdf_lean_mass_trend_kg != null) {
            const val = w.pdf_lean_mass_trend_kg;
            leanMassTrendEl.textContent = (val >= 0 ? '+' : '') + val + ' kg';
            leanMassTrendEl.className = 'stat-value ' + (val < 0 ? 'negative' : val > 0 ? 'positive' : '');
            leanMassTrendStat.style.display = '';
        } else {
            leanMassTrendStat.style.display = 'none';
        }

        // Weight chart (no daily body fat - too noisy for home bioimpedance)
        const history = w.weight_history || [];
        if (history.length > 0) {
            renderWeightChart(history, null);
        }

        // Nutrition
        const nutrition = data.nutrition || {};
        document.getElementById('avgCalories').textContent = nutrition.avg_calories ?? '--';
        document.getElementById('avgProtein').textContent = nutrition.avg_protein_g ?? '--';
        document.getElementById('avgFiber').textContent = nutrition.avg_fiber_g ?? '--';
        document.getElementById('avgSodium').textContent = nutrition.avg_sodium_mg ?? '--';
        document.getElementById('avgCarbs').textContent = nutrition.avg_carbs_g ?? '--';
        document.getElementById('avgFat').textContent = nutrition.avg_fat_g ?? '--';
        document.getElementById('daysLogged').textContent = nutrition.days_logged ?? 0;
        document.getElementById('daysTarget').textContent = nutrition.days_1800_to_1950 ?? 0;
        document.getElementById('daysBelow').textContent = nutrition.days_below_1600 ?? 0;
        document.getElementById('daysAbove').textContent = nutrition.days_above_2200 ?? 0;
        document.getElementById('daysProtein').textContent = nutrition.days_protein_170_plus ?? 0;
        document.getElementById('daysFiber').textContent = nutrition.days_fiber_20_plus ?? 0;
        const targets = data.meta?.adherence_targets || nutrition.adherence_targets;
        if (targets) {
            const [calLo, calHi] = targets.calorie_range || [1800, 1950];
            document.getElementById('calRangeLabel').textContent = calLo + '-' + calHi;
            document.getElementById('calLowLabel').textContent = nutrition.calorie_low_threshold ?? calLo - 200;
            document.getElementById('calHighLabel').textContent = nutrition.calorie_high_threshold ?? calHi + 250;
            document.getElementById('proteinTargetLabel').textContent = targets.protein_g ?? 170;
            document.getElementById('fiberTargetLabel').textContent = targets.fiber_g ?? 20;
        } else {
            document.getElementById('calRangeLabel').textContent = '1800-1950';
            document.getElementById('calLowLabel').textContent = '1600';
            document.getElementById('calHighLabel').textContent = '2200';
            document.getElementById('proteinTargetLabel').textContent = '170';
            document.getElementById('fiberTargetLabel').textContent = '20';
        }

        const sugarSection = document.getElementById('sugarSection');
        if (nutrition.avg_sugar_g != null) {
            document.getElementById('avgSugar').textContent = nutrition.avg_sugar_g;
            document.getElementById('daysHighSugar').textContent = nutrition.days_high_sugar ?? 0;
            sugarSection.style.display = '';
        } else {
            sugarSection.style.display = 'none';
        }

        const fatProfileSection = document.getElementById('fatProfileSection');
        if (nutrition.fat_profile) {
            const fp = nutrition.fat_profile;
            fatProfileSection.innerHTML = '<p><strong>Perfil de gorduras:</strong> Saturada ' + (fp.fat_saturated_g ?? '--') + 'g, Poli ' + (fp.fat_poly_g ?? '--') + 'g, Mono ' + (fp.fat_mono_g ?? '--') + 'g</p>';
            fatProfileSection.style.display = '';
        } else {
            fatProfileSection.style.display = 'none';
        }

        const caloriesByMealSection = document.getElementById('caloriesByMealSection');
        if (nutrition.calories_by_meal && Object.keys(nutrition.calories_by_meal).length > 0) {
            const parts = Object.entries(nutrition.calories_by_meal).map(([meal, cal]) => meal + ': ' + cal + ' kcal');
            caloriesByMealSection.innerHTML = '<p><strong>Calorias por refeição (média):</strong> ' + parts.join(', ') + '</p>';
            caloriesByMealSection.style.display = '';
        } else {
            caloriesByMealSection.style.display = 'none';
        }

        const nutritionHistory = nutrition.nutrition_history || [];
        if (nutritionHistory.length > 0) {
            renderNutritionChart(nutritionHistory);
        } else if (nutritionChart) {
            nutritionChart.destroy();
            nutritionChart = null;
        }

        // Exercise
        const e = data.exercise || {};
        document.getElementById('exerciseDays').textContent = e.days_logged ?? '--';
        const avgMin = e.avg_exercise_minutes;
        const avgSteps = e.avg_steps;
        const avgExCal = e.avg_exercise_calories;

        const minStat = document.getElementById('avgMinutesStat');
        const stepsStat = document.getElementById('avgStepsStat');
        const calStat = document.getElementById('avgCaloriesStat');

        document.getElementById('avgMinutes').textContent = avgMin != null ? avgMin.toFixed(0) : '--';
        document.getElementById('avgSteps').textContent = avgSteps != null ? avgSteps.toFixed(0) : '--';
        document.getElementById('avgExerciseCal').textContent = avgExCal != null ? avgExCal.toFixed(0) : '--';

        minStat.style.display = avgMin != null ? '' : 'none';
        stepsStat.style.display = avgSteps != null ? '' : 'none';
        calStat.style.display = avgExCal != null ? '' : 'none';

        const sessionCounts = e.session_type_counts;
        const sessionEl = document.getElementById('sessionTypeCounts');
        if (sessionCounts && Object.keys(sessionCounts).length > 0) {
            const parts = Object.entries(sessionCounts).map(([k, v]) => {
                const label = k === 'treadmill' ? 'Esteira' : k === 'other' ? 'Outros' : k;
                return `${label}: ${v} dias`;
            });
            sessionEl.textContent = parts.join(' | ');
            sessionEl.style.display = '';
        } else {
            sessionEl.style.display = 'none';
        }

        const exerciseHistory = e.exercise_history || [];
        if (exerciseHistory.length > 0) {
            renderExerciseChart(exerciseHistory);
        } else if (exerciseChart) {
            exerciseChart.destroy();
            exerciseChart = null;
        }

        // Comparison
        const comp = data.comparison || {};
        const compContainer = document.getElementById('comparisonMetrics');
        const compEntries = [];
        if (comp.weight_mfp_kg != null) compEntries.push({ k: 'Peso MFP (kg)', v: comp.weight_mfp_kg });
        if (comp.weight_withings_kg != null) compEntries.push({ k: 'Peso Withings (kg)', v: comp.weight_withings_kg });
        if (comp.steps_mfp != null) compEntries.push({ k: 'Passos MFP/dia', v: comp.steps_mfp });
        if (comp.steps_withings != null) compEntries.push({ k: 'Passos Withings/dia', v: comp.steps_withings });
        if (compEntries.length === 0) {
            compContainer.innerHTML = '<p class="empty-state">Nenhum dado para comparar</p>';
        } else {
            compContainer.innerHTML = compEntries.map(({ k, v }) =>
                `<div class="metric-row"><span class="metric-key">${k}</span><span class="metric-value">${v}</span></div>`
            ).join('');
        }

        // PDF report v2 (activity, body, sleep, cardio)
        const pdfV2 = data.pdf_report_v2 || {};
        const pdfV2Labels = {
            avg_daily_steps: 'Passos/dia', avg_active_minutes: 'Min ativos', days_over_10k_pct: 'Dias acima de 10k (%)', days_under_2k_pct: 'Dias abaixo de 2k (%)',
            latest_weight_kg: 'Peso (kg)', bmi_avg: 'IMC', bmr_kcal: 'BMR (kcal)', fat_mass_kg: 'Massa gorda (kg)', muscle_mass_kg: 'Massa muscular (kg)',
            lean_mass_kg: 'Massa magra (kg)', water_mass_kg: 'Água (kg)', bone_mass_kg: 'Massa óssea (kg)', visceral_fat: 'Gordura visceral',
            derived_fat_mass_pct: 'Gordura corporal estimada (%)', derived_lean_mass_pct: 'Massa magra (%)',
            total_sleep_time: 'Sono total', efficiency_pct: 'Eficiência (%)', nights_over_7h_pct: 'Noites acima de 7h (%)', nights_under_5h_pct: 'Noites abaixo de 5h (%)',
            time_in_bed: 'Tempo na cama', sleep_latency_sec: 'Latência do sono (s)', snoring_min: 'Ronco (min)', overnight_hr_bpm: 'FC noturna (bpm)', nights: 'Noites',
            awake_hr_avg_bpm: 'FC acordado (bpm)', asleep_hr_avg_bpm: 'FC dormindo (bpm)', pwv_m_per_s: 'Velocidade onda de pulso (m/s)',
            awake_spo2_avg_pct: 'SpO2 médio (%)', awake_spo2_min_pct: 'SpO2 mínimo (%)', measurements_under_90_pct: 'Medições SpO2 &lt;90%',
        };
        const renderPdfV2Block = (blockData, containerId) => {
            const el = document.getElementById(containerId);
            if (!el) return;
            if (!blockData || Object.keys(blockData).length === 0) {
                el.innerHTML = '<p class="empty-state">Sem dados</p>';
                return;
            }
            const rows = Object.entries(blockData).filter(([, v]) => v != null && v !== '').map(([k, v]) => {
                const label = pdfV2Labels[k] || k.replace(/_/g, ' ');
                return '<div class="metric-row"><span class="metric-key">' + label + '</span><span class="metric-value">' + v + '</span></div>';
            });
            el.innerHTML = rows.join('');
        };
        renderPdfV2Block(pdfV2.activity, 'pdfV2Activity');
        renderPdfV2Block(pdfV2.body, 'pdfV2Body');
        renderPdfV2Block(pdfV2.sleep, 'pdfV2Sleep');
        renderPdfV2Block(pdfV2.cardio, 'pdfV2Cardio');

        // Weekly summary
        const weeklySummary = data.weekly_summary || [];
        const weeklyContainer = document.getElementById('weeklySummary');
        if (weeklySummary.length > 0) {
            weeklyContainer.innerHTML = weeklySummary.map(w => {
                const rows = [
                    ['Peso médio', (w.avg_weight_kg != null ? w.avg_weight_kg + ' kg' : '--')],
                    ['Calorias', w.avg_calories ?? '--'],
                    ['Min exercício', w.avg_exercise_minutes ?? '--'],
                    ['Passos', w.avg_steps ?? '--'],
                ].map(([k, v]) =>
                    '<div class="metric-row"><span class="metric-key">' + k + '</span><span class="metric-value">' + v + '</span></div>'
                ).join('');
                return '<div class="week-block"><div class="week-header">' + w.week + '</div>' + rows + '</div>';
            }).join('');
        } else {
            weeklyContainer.innerHTML = '<p class="empty-state">Nenhum dado semanal</p>';
        }

        // Alerts (categorized: critical, warning, info)
        const alertsData = data.alerts || {};
        const critical = alertsData.critical || [];
        const warning = alertsData.warning || [];
        const info = alertsData.info || [];
        const alertsContainer = document.getElementById('alertsList');
        const allAlerts = [
            ...critical.map(a => ({ text: a, cls: 'alert-critical' })),
            ...warning.map(a => ({ text: a, cls: 'alert-warning' })),
            ...info.map(a => ({ text: a, cls: 'alert-info' })),
        ];
        if (allAlerts.length > 0) {
            alertsContainer.innerHTML = '<ul class="alerts-list">' + allAlerts.map(a =>
                '<li class="alert-item ' + a.cls + '">' + a.text + '</li>'
            ).join('') + '</ul>';
        } else {
            alertsContainer.innerHTML = '<p class="empty-state">Nenhum alerta</p>';
        }

        // Weekly adherence
        const weeklyAdherence = data.weekly_adherence || [];
        const adherenceContainer = document.getElementById('weeklyAdherence');
        if (adherenceContainer) {
            if (weeklyAdherence.length > 0) {
                adherenceContainer.innerHTML = weeklyAdherence.map(w => {
                    const comp = w.components || {};
                    const rows = [
                        ['Score', w.score + ' <span class="rating-badge">' + (w.rating || '') + '</span>'],
                        ['Calorias', (comp.calories_score ?? '--') + '/30'],
                        ['Proteína', (comp.protein_score ?? '--') + '/25'],
                        ['Fibra', (comp.fiber_score ?? '--') + '/15'],
                        ['Sódio', (comp.sodium_hydration_score ?? '--') + '/10'],
                        ['Treino', (comp.training_score ?? '--') + '/20'],
                    ];
                    return '<div class="adherence-block"><div class="adherence-header">' + w.week_start + ' a ' + w.week_end + '</div>' +
                        rows.map(([k, v]) => '<div class="metric-row"><span class="metric-key">' + k + '</span><span class="metric-value">' + v + '</span></div>').join('') +
                        '</div>';
                }).join('');
            } else {
                adherenceContainer.innerHTML = '<p class="empty-state">Nenhum dado de aderência</p>';
            }
        }

        // Projection
        const projection = data.projection || {};
        const projContainer = document.getElementById('projectionContent');
        if (projContainer && Object.keys(projection).length > 0) {
            const sc = projection.scenarios || {};
            const labels = { pessimistic: 'Pessimista', realistic: 'Realista', optimistic: 'Otimista' };
            const rows = [
                ['Data alvo', projection.target_date || '--'],
                ['MA7 atual', (projection.current_ma7_kg ?? '--') + ' kg'],
            ];
            for (const [key, label] of Object.entries(labels)) {
                const s = sc[key];
                if (s && s.projected_ma7_kg != null) {
                    rows.push([label, s.projected_ma7_kg + ' kg']);
                }
            }
            let html = rows.map(([k, v]) =>
                '<div class="metric-row"><span class="metric-key">' + k + '</span><span class="metric-value">' + v + '</span></div>'
            ).join('');
            if (projection.note) {
                html += '<p class="projection-note">' + projection.note + '</p>';
            }
            projContainer.innerHTML = html;
        } else if (projContainer) {
            projContainer.innerHTML = '<p class="empty-state">Dados insuficientes para projeção</p>';
        }

        // Retention flag
        const retention = data.retention_flag || {};
        const retentionContainer = document.getElementById('retentionFlagContent');
        if (retentionContainer) {
            if (Object.keys(retention).length > 0) {
                const isRetention = retention.is_probable_retention;
                const reasons = (retention.reason_codes || []).map(r => {
                    const labels = { weight_up_short_term: 'Peso subiu', ma7_stable_or_down: 'MA7 estável', recent_high_sodium: 'Sódio alto', recent_calories_out_of_range: 'Calorias fora da faixa', recent_low_fiber: 'Fibra baixa' };
                    return labels[r] || r;
                }).join(', ');
                const metrics = retention.metrics || {};
                const rows = [
                    ['Status', '<span class="retention-status ' + (isRetention ? 'yes' : 'no') + '">' + (isRetention ? 'Retenção provável' : 'Sem retenção') + '</span>'],
                    ['Variação 3 dias', (metrics.weight_change_3d_kg ?? '--') + ' kg'],
                ];
                if (reasons) rows.push(['Motivos', reasons]);
                retentionContainer.innerHTML = rows.map(([k, v]) =>
                    '<div class="metric-row"><span class="metric-key">' + k + '</span><span class="metric-value">' + v + '</span></div>'
                ).join('');
            } else {
                retentionContainer.innerHTML = '<p class="empty-state">Dados insuficientes</p>';
            }
        }

        // Sleep
        const sleep = data.sleep || {};
        const sleepContainer = document.getElementById('sleepContent');
        if (sleepContainer) {
            if (Object.keys(sleep).length > 0) {
                const rows = [];
                if (sleep.avg_duration) rows.push(['Duração média', sleep.avg_duration]);
                if (sleep.avg_efficiency_pct != null) rows.push(['Eficiência', sleep.avg_efficiency_pct + '%']);
                sleepContainer.innerHTML = rows.map(([k, v]) =>
                    '<div class="metric-row"><span class="metric-key">' + k + '</span><span class="metric-value">' + v + '</span></div>'
                ).join('');
            } else {
                sleepContainer.innerHTML = '<p class="empty-state">Sem dados de sono</p>';
            }
        }
    }

    function renderWeightChart(history, bodyFatHistory) {
        const ctx = document.getElementById('weightChart').getContext('2d');

        if (weightChart) {
            weightChart.destroy();
        }

        const labels = history.map(h => h.date);
        const weights = history.map(h => h.weight);
        const ma5 = history.map(h => h.ma5);
        const ma7 = history.map(h => h.ma7);

        const bodyFatMap = {};
        if (bodyFatHistory && bodyFatHistory.length > 0) {
            bodyFatHistory.forEach(h => { bodyFatMap[h.date] = h.body_fat_pct; });
        }
        const bodyFatData = labels.map(d => bodyFatMap[d] ?? null);

        const datasets = [
            {
                label: 'Peso (kg)',
                data: weights,
                borderColor: '#14b8a6',
                backgroundColor: 'rgba(20, 184, 166, 0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 2,
            },
        ];

        if (ma5.some(v => v != null)) {
            datasets.push({
                label: 'MA5',
                data: ma5,
                borderColor: '#5eead4',
                borderDash: [4, 4],
                fill: false,
                tension: 0.3,
                pointRadius: 0,
            });
        }

        if (ma7.some(v => v != null)) {
            datasets.push({
                label: 'MA7',
                data: ma7,
                borderColor: '#99f6e4',
                borderDash: [2, 2],
                fill: false,
                tension: 0.3,
                pointRadius: 0,
            });
        }

        if (bodyFatData.some(v => v != null)) {
            datasets.push({
                label: 'Gordura corporal %',
                data: bodyFatData,
                borderColor: '#f59e0b',
                borderDash: [6, 6],
                fill: false,
                tension: 0.3,
                pointRadius: 2,
                yAxisID: 'yBodyFat',
            });
        }

        const scales = {
            x: {
                ticks: { color: '#9ca3af', maxTicksLimit: 10 },
                grid: { color: '#2d3a4d' },
            },
            y: {
                ticks: { color: '#9ca3af' },
                grid: { color: '#2d3a4d' },
            },
        };
        if (bodyFatData.some(v => v != null)) {
            scales.yBodyFat = {
                position: 'right',
                ticks: { color: '#f59e0b' },
                grid: { display: false },
            };
        }

        weightChart = new Chart(ctx, {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: '#9ca3af' },
                    },
                },
                scales: scales,
            },
        });
    }

    function renderNutritionChart(history) {
        const ctx = document.getElementById('nutritionChart');
        if (!ctx) return;

        if (nutritionChart) {
            nutritionChart.destroy();
        }

        const labels = history.map(h => h.date);
        const calories = history.map(h => h.calories);

        nutritionChart = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Calorias (kcal)',
                    data: calories,
                    borderColor: '#14b8a6',
                    backgroundColor: 'rgba(20, 184, 166, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#9ca3af' } } },
                scales: {
                    x: { ticks: { color: '#9ca3af', maxTicksLimit: 10 }, grid: { color: '#2d3a4d' } },
                    y: { ticks: { color: '#9ca3af' }, grid: { color: '#2d3a4d' } },
                },
            },
        });
    }

    function renderExerciseChart(history) {
        const ctx = document.getElementById('exerciseChart');
        if (!ctx) return;

        if (exerciseChart) {
            exerciseChart.destroy();
        }

        const labels = history.map(h => h.date);
        const minutes = history.map(h => h.exercise_minutes ?? 0);
        const steps = history.map(h => h.steps ?? 0);

        const datasets = [];
        if (minutes.some(v => v > 0)) {
            datasets.push({
                label: 'Minutos',
                data: minutes,
                backgroundColor: 'rgba(20, 184, 166, 0.6)',
                borderColor: '#14b8a6',
            });
        }
        if (steps.some(v => v > 0)) {
            datasets.push({
                label: 'Passos',
                data: steps,
                backgroundColor: 'rgba(94, 234, 212, 0.5)',
                borderColor: '#5eead4',
            });
        }

        if (datasets.length === 0) return;

        exerciseChart = new Chart(ctx.getContext('2d'), {
            type: 'bar',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#9ca3af' } } },
                scales: {
                    x: { ticks: { color: '#9ca3af', maxTicksLimit: 10 }, grid: { color: '#2d3a4d' } },
                    y: { ticks: { color: '#9ca3af' }, grid: { color: '#2d3a4d' } },
                },
            },
        });
    }
})();
