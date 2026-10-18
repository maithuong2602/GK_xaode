/**
 * Exam Shuffler - Frontend Application Controller
 * Handles 6-step teacher wizard, API interactions, dynamic DOM rendering.
 */

const app = {
  currentStep: 1,
  sessionId: null,
  analysis: null,
  thumbnails: [],
  lockedQuestionIds: new Set(),
  customAnswers: {},
  questionTypeOverrides: {},
  sectionConfigs: {},
  variants: {},
  activePreviewCode: null,
  previewCopyMode: 'teacher',   // 'teacher' or 'student'
  step5Tab: 'single',           // 'single' or 'matrix'
  exportTargetCode: null,
  exportModalSelectedOption: 'student',

  init() {
    this.setupDragAndDrop();
    this.updateVariantCodesPreview();
  },

  showLoader(text = "Đang xử lý dữ liệu...") {
    const overlay = document.getElementById("loaderOverlay");
    const loaderText = document.getElementById("loaderText");
    if (loaderText) loaderText.textContent = text;
    if (overlay) overlay.classList.add("active");
  },

  hideLoader() {
    const overlay = document.getElementById("loaderOverlay");
    if (overlay) overlay.classList.remove("active");
  },

  goToStep(stepNumber) {
    if (stepNumber < 1 || stepNumber > 6) return;

    // Validate navigation forward
    if (stepNumber > 1 && !this.sessionId) {
      alert("Vui lòng tải lên hoặc chọn một tệp đề thi trước.");
      return;
    }
    if (stepNumber > 4 && Object.keys(this.variants).length === 0) {
      alert("Vui lòng thực hiện cấu hình và bấm 'Bắt đầu sinh mã đề' trước.");
      return;
    }

    this.currentStep = stepNumber;

    // Update Stepper Nav UI
    for (let i = 1; i <= 6; i++) {
      const navBtn = document.getElementById(`stepNav${i}`);
      const contentSec = document.getElementById(`step${i}`);

      if (navBtn) {
        navBtn.classList.remove("active");
        if (i < stepNumber) {
          navBtn.classList.add("completed");
          navBtn.disabled = false;
        } else if (i === stepNumber) {
          navBtn.classList.add("active");
          navBtn.disabled = false;
        }
      }

      if (contentSec) {
        contentSec.classList.remove("active");
        if (i === stepNumber) {
          contentSec.classList.add("active");
        }
      }
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
  },

  setupDragAndDrop() {
    const dropzone = document.getElementById("dropzone");
    if (!dropzone) return;

    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.add("drag-over");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.remove("drag-over");
      });
    });

    dropzone.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        this.uploadFile(files[0]);
      }
    });
  },

  handleFileSelect(event) {
    const files = event.target.files;
    if (files && files.length > 0) {
      this.uploadFile(files[0]);
    }
  },

  async uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    this.showLoader(`Đang đọc và phân tích ${file.name}...`);
    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Không thể tải lên file.");
      }

      const data = await res.json();
      this.sessionId = data.session_id;
      this.analysis = data.analysis;
      this.thumbnails = data.thumbnails || [];

      // Reset state for new document
      this.lockedQuestionIds.clear();
      this.customAnswers = {};
      this.questionTypeOverrides = {};
      this.variants = {};

      // Initialize answers from analysis
      if (this.analysis.detected_answers) {
        for (const [qNum, ans] of Object.entries(this.analysis.detected_answers)) {
          this.customAnswers[`q_${qNum}`] = ans;
        }
      }

      // Initialize section configs
      this.analysis.sections.forEach((sec) => {
        this.sectionConfigs[sec.id] = {
          shuffle_questions: sec.shuffle_questions,
          shuffle_options: sec.shuffle_options,
        };
      });

      document.getElementById("btnResetApp").style.display = "inline-flex";

      this.renderStep2();
      this.renderStep3();
      this.renderStep4Sections();
      this.goToStep(2);
    } catch (error) {
      alert(`Lỗi: ${error.message}`);
    } finally {
      this.hideLoader();
    }
  },

  async loadSample(filename) {
    this.showLoader(`Đang nạp dữ liệu đề thi mẫu: ${filename}...`);
    try {
      const res = await fetch(`/api/load-sample/${encodeURIComponent(filename)}`, {
        method: "POST",
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Không thể nạp file mẫu.");
      }

      const data = await res.json();
      this.sessionId = data.session_id;
      this.analysis = data.analysis;
      this.thumbnails = data.thumbnails || [];

      this.lockedQuestionIds.clear();
      this.customAnswers = {};
      this.questionTypeOverrides = {};
      this.variants = {};

      if (this.analysis.detected_answers) {
        for (const [qNum, ans] of Object.entries(this.analysis.detected_answers)) {
          this.customAnswers[`q_${qNum}`] = ans;
        }
      }

      this.analysis.sections.forEach((sec) => {
        this.sectionConfigs[sec.id] = {
          shuffle_questions: sec.shuffle_questions,
          shuffle_options: sec.shuffle_options,
        };
      });

      document.getElementById("btnResetApp").style.display = "inline-flex";

      this.renderStep2();
      this.renderStep3();
      this.renderStep4Sections();
      this.goToStep(2);
    } catch (error) {
      alert(`Lỗi: ${error.message}`);
    } finally {
      this.hideLoader();
    }
  },

  renderStep2() {
    if (!this.analysis) return;

    document.getElementById("analysisFileName").textContent = `Tệp: ${this.analysis.filename} (${this.analysis.file_type.toUpperCase()})`;
    document.getElementById("statTotalQ").textContent = this.analysis.total_questions;
    document.getElementById("statMcQ").textContent = this.analysis.num_mc_questions;
    document.getElementById("statTfQ").textContent = this.analysis.num_tf_questions;
    document.getElementById("statEssayQ").textContent = this.analysis.num_essay_questions;

    const warnBox = document.getElementById("pdfWarningBox");
    const warnText = document.getElementById("pdfWarningText");
    if (this.analysis.pdf_warning) {
      warnBox.style.display = "flex";
      warnText.innerHTML = this.analysis.pdf_warning.replace(/\n/g, "<br>");
    } else {
      warnBox.style.display = "none";
    }

    const secList = document.getElementById("sectionsOverviewList");
    secList.innerHTML = "";

    this.analysis.sections.forEach((sec) => {
      const item = document.createElement("div");
      item.className = "stat-card";
      item.style.padding = "0.85rem 1.25rem";
      item.innerHTML = `
        <div style="font-weight:700; color:#1e3a8a; min-width:30px;">#${sec.id}</div>
        <div style="flex-grow:1;">
          <div style="font-weight:600; color:#1e293b;">${sec.title}</div>
          <div style="font-size:0.8rem; color:#64748b;">Số lượng: ${sec.question_ids.length} câu hỏi</div>
        </div>
        <div>
          <span class="badge-tag" style="background:#eff6ff; color:#2563eb;">
            ${sec.shuffle_questions ? "Cho phép xáo câu" : "Khóa vị trí câu"}
          </span>
        </div>
      `;
      secList.appendChild(item);
    });
  },

  renderStep3() {
    if (!this.analysis) return;

    const container = document.getElementById("questionsList");
    container.innerHTML = "";

    let answeredCount = 0;
    this.analysis.questions.forEach((q) => {
      const currentAns = this.customAnswers[q.id] || q.correct_answer || "";
      if (currentAns) answeredCount++;

      const isLocked = this.lockedQuestionIds.has(q.id);

      const card = document.createElement("div");
      card.className = `question-card ${isLocked ? "locked" : ""}`;
      card.id = `card_${q.id}`;

      // Badge type
      let badgeClass = "q-badge-mc";
      let badgeText = "Trắc nghiệm A-D";
      if (q.question_type === "TRUE_FALSE") {
        badgeClass = "q-badge-tf";
        badgeText = "Đúng / Sai";
      } else if (q.question_type === "ESSAY") {
        badgeClass = "q-badge-essay";
        badgeText = "Tự luận";
      }

      // Options HTML
      let optionsHtml = "";
      if (q.options && q.options.length > 0) {
        optionsHtml = `<div class="q-options-grid">`;
        q.options.forEach((opt) => {
          const isSelected = currentAns.toUpperCase() === opt.letter.toUpperCase();
          optionsHtml += `
            <div class="q-opt-item ${isSelected ? "is-correct" : ""}" id="opt_${q.id}_${opt.letter}">
              <span class="opt-letter-tag">${opt.letter}.</span>
              <span>${opt.text || opt.full_text}</span>
            </div>
          `;
        });
        optionsHtml += `</div>`;
      }

      // Answers Selector HTML
      let ansSelectorHtml = "";
      if (q.question_type === "MULTIPLE_CHOICE") {
        ansSelectorHtml = `
          <div class="ans-selector-wrap">
            <span style="font-weight:600; color:#475569;">Đáp án đúng:</span>
            <div class="ans-btn-group">
              ${["A", "B", "C", "D"]
                .map(
                  (let) => `
                <button type="button" class="ans-btn ${currentAns.toUpperCase() === let ? "selected" : ""}" 
                  onclick="app.selectAnswer('${q.id}', '${let}')">${let}</button>
              `
                )
                .join("")}
            </div>
          </div>
        `;
      } else if (q.question_type === "TRUE_FALSE") {
        ansSelectorHtml = `
          <div class="ans-selector-wrap">
            <span style="font-weight:600; color:#475569;">Đáp án:</span>
            <div class="ans-btn-group">
              <button type="button" class="ans-btn ${currentAns.toLowerCase() === "đúng" ? "selected" : ""}" 
                style="width:auto; padding:0 0.5rem;" onclick="app.selectAnswer('${q.id}', 'Đúng')">Đúng</button>
              <button type="button" class="ans-btn ${currentAns.toLowerCase() === "sai" ? "selected" : ""}" 
                style="width:auto; padding:0 0.5rem;" onclick="app.selectAnswer('${q.id}', 'Sai')">Sai</button>
            </div>
          </div>
        `;
      }

      card.innerHTML = `
        <div class="q-header">
          <div class="q-title-wrap">
            <strong style="color:#1e3a8a; font-size:1.05rem;">Câu ${q.original_number}</strong>
            <span class="q-badge ${badgeClass}">${badgeText}</span>
            ${q.has_tables ? '<span class="badge-tag" style="background:#f1f5f9; font-size:0.75rem;">📊 Có Bảng</span>' : ""}
            ${q.has_images ? '<span class="badge-tag" style="background:#f1f5f9; font-size:0.75rem;">🖼️ Có Hình</span>' : ""}
          </div>
          <div class="q-actions">
            <button type="button" class="toggle-lock-btn ${isLocked ? "locked" : ""}" onclick="app.toggleLock('${q.id}')">
              ${isLocked ? "🔒 Đã khóa vị trí" : "🔓 Không khóa"}
            </button>
          </div>
        </div>

        <div class="q-lead-text">${q.lead_text}</div>
        ${optionsHtml}

        <div class="q-controls-bar">
          ${ansSelectorHtml}
          <div style="font-size:0.8rem; color:#94a3b8;">
            Vị trí gốc: Thẻ XML ${q.start_body_idx}-${q.end_body_idx}
          </div>
        </div>
      `;

      container.appendChild(card);
    });

    document.getElementById("answersSummaryText").innerHTML = `
      Đã có đáp án cho: <strong>${answeredCount}/${this.analysis.total_questions}</strong> câu hỏi
    `;
  },

  toggleLock(qId) {
    if (this.lockedQuestionIds.has(qId)) {
      this.lockedQuestionIds.delete(qId);
    } else {
      this.lockedQuestionIds.add(qId);
    }
    this.renderStep3();
  },

  selectAnswer(qId, letter) {
    this.customAnswers[qId] = letter;
    this.renderStep3();
  },

  openPasteAnswerModal() {
    document.getElementById("pasteAnswerModal").classList.add("active");
    document.getElementById("rawAnswerInput").focus();
  },

  closePasteAnswerModal() {
    document.getElementById("pasteAnswerModal").classList.remove("active");
  },

  async applyPastedAnswers() {
    const rawText = document.getElementById("rawAnswerInput").value.trim();
    if (!rawText) return;

    try {
      const res = await fetch("/api/parse-answers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_text: rawText }),
      });

      const data = await res.json();
      if (data.answers) {
        for (const [qNum, ans] of Object.entries(data.answers)) {
          this.customAnswers[`q_${qNum}`] = ans;
        }
        this.closePasteAnswerModal();
        this.renderStep3();
        alert(`Đã áp dụng thành công ${data.count} đáp án!`);
      }
    } catch (e) {
      alert("Không thể phân tích chuỗi đáp án.");
    }
  },

  autoFillAnswersFromDoc() {
    if (!this.analysis || !this.analysis.detected_answers) return;
    for (const [qNum, ans] of Object.entries(this.analysis.detected_answers)) {
      this.customAnswers[`q_${qNum}`] = ans;
    }
    this.renderStep3();
    alert("Đã khôi phục đáp án gốc từ tài liệu!");
  },

  renderStep4Sections() {
    if (!this.analysis) return;
    const container = document.getElementById("sectionsConfigContainer");
    container.innerHTML = "";

    this.analysis.sections.forEach((sec) => {
      const cfg = this.sectionConfigs[sec.id] || {
        shuffle_questions: true,
        shuffle_options: true,
      };

      const card = document.createElement("div");
      card.className = "section-config-card";
      card.innerHTML = `
        <div class="sec-title">Phần ${sec.id}: ${sec.title}</div>
        <label class="checkbox-label">
          <input type="checkbox" id="chk_sec_q_${sec.id}" ${cfg.shuffle_questions ? "checked" : ""} 
            onchange="app.updateSecConfig(${sec.id}, 'shuffle_questions', this.checked)">
          <span>Xáo thứ tự các câu hỏi trong phần này</span>
        </label>
        <label class="checkbox-label">
          <input type="checkbox" id="chk_sec_opt_${sec.id}" ${cfg.shuffle_options ? "checked" : ""} 
            onchange="app.updateSecConfig(${sec.id}, 'shuffle_options', this.checked)">
          <span>Xáo thứ tự các phương án (A, B, C, D)</span>
        </label>
      `;
      container.appendChild(card);
    });
  },

  updateSecConfig(secId, key, val) {
    if (!this.sectionConfigs[secId]) {
      this.sectionConfigs[secId] = { shuffle_questions: true, shuffle_options: true };
    }
    this.sectionConfigs[secId][key] = val;
  },

  updateVariantCodesPreview() {
    const num = parseInt(document.getElementById("inputNumVariants").value) || 4;
    const start = parseInt(document.getElementById("inputStartCode").value) || 101;
    const container = document.getElementById("previewVariantCodesList");

    container.innerHTML = "";
    for (let i = 0; i < num; i++) {
      const badge = document.createElement("span");
      badge.className = "badge-tag";
      badge.style.background = "#eff6ff";
      badge.textContent = String(start + i);
      container.appendChild(badge);
    }
  },

  randomizeSeed() {
    const newSeed = Math.floor(10000000 + Math.random() * 90000000);
    document.getElementById("inputSeed").value = newSeed;
  },

  async executeShuffle() {
    if (!this.sessionId) return;

    const numVariants = parseInt(document.getElementById("inputNumVariants").value) || 4;
    const startCode = parseInt(document.getElementById("inputStartCode").value) || 101;
    const seed = parseInt(document.getElementById("inputSeed").value) || 20261018;
    const keepWithNext = document.getElementById("chkKeepWithNext").checked;

    const payload = {
      num_variants: numVariants,
      start_code: startCode,
      seed: seed,
      keep_with_next: keepWithNext,
      section_configs: this.sectionConfigs,
      locked_question_ids: Array.from(this.lockedQuestionIds),
      custom_answers: this.customAnswers,
      question_type_overrides: this.questionTypeOverrides,
    };

    this.showLoader(`Đang sinh ${numVariants} mã đề và tối ưu hóa cấu trúc XML...`);
    try {
      const res = await fetch(`/api/shuffle/${this.sessionId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Không thể xáo đề.");
      }

      const data = await res.json();
      this.variants = data.variants;

      this.renderStep5();
      this.renderStep6();
      this.goToStep(5);
    } catch (e) {
      alert(`Lỗi xáo đề: ${e.message}`);
    } finally {
      this.hideLoader();
    }
  },

  switchStep5Tab(tab) {
    this.step5Tab = tab;
    const btnSingle = document.getElementById("tabBtnPerVariant");
    const btnMatrix = document.getElementById("tabBtnMatrix");
    const areaSingle = document.getElementById("singleVariantViewArea");
    const areaMatrix = document.getElementById("matrixViewArea");

    if (tab === "matrix") {
      btnSingle.classList.remove("active");
      btnMatrix.classList.add("active");
      areaSingle.style.display = "none";
      areaMatrix.style.display = "block";
      this.renderPositionMatrix();
    } else {
      btnMatrix.classList.remove("active");
      btnSingle.classList.add("active");
      areaMatrix.style.display = "none";
      areaSingle.style.display = "block";
    }
  },

  setPreviewCopyMode(mode) {
    this.previewCopyMode = mode;
    const btnTeacher = document.getElementById("btnPreviewTeacherMode");
    const btnStudent = document.getElementById("btnPreviewStudentMode");
    const desc = document.getElementById("previewModeDescription");

    if (mode === "student") {
      btnTeacher.classList.remove("active");
      btnStudent.classList.add("active");
      desc.textContent = "Đang hiển thị bản học sinh (đề thi sạch, ẩn đáp án)";
      desc.style.color = "#2563eb";
      desc.style.background = "#eff6ff";
    } else {
      btnStudent.classList.remove("active");
      btnTeacher.classList.add("active");
      desc.textContent = "Đang hiển thị bản giáo viên (có đáp án và chú thích câu gốc)";
      desc.style.color = "#059669";
      desc.style.background = "#ecfdf5";
    }

    if (this.activePreviewCode) {
      this.selectPreviewVariant(this.activePreviewCode);
    }
  },

  renderStep5() {
    const codes = Object.keys(this.variants);
    if (codes.length === 0) return;

    // Render variant tabs
    const tabsContainer = document.getElementById("variantTabs");
    tabsContainer.innerHTML = "";

    codes.forEach((code, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `preview-tab-btn ${idx === 0 ? "active" : ""}`;
      btn.textContent = `Mã ${code}`;
      btn.onclick = () => this.selectPreviewVariant(code);
      tabsContainer.appendChild(btn);
    });

    this.selectPreviewVariant(codes[0]);
    this.renderPositionMatrix();
  },

  selectPreviewVariant(code) {
    this.activePreviewCode = code;

    // Update active tab styling
    document.querySelectorAll(".preview-tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.textContent === `Mã ${code}`);
    });

    document.getElementById("currentPreviewHeading").textContent = `Chi tiết đối chiếu: Mã đề ${code}`;

    const varData = this.variants[code];
    if (!varData) return;

    // Render Integrity Checklist
    const integrityList = document.getElementById("integrityList");
    integrityList.innerHTML = "";
    varData.integrity.messages.forEach((msg) => {
      const li = document.createElement("li");
      li.textContent = msg;
      integrityList.appendChild(li);
    });

    // Toggle Answer Columns in header based on mode
    const isTeacher = this.previewCopyMode === "teacher";
    document.querySelectorAll("#variantMappingTable th.col-answer").forEach((th) => {
      th.style.display = isTeacher ? "table-cell" : "none";
    });

    // Render Mapping Table
    const tbody = document.getElementById("variantMappingBody");
    tbody.innerHTML = "";

    varData.question_mappings.forEach((m) => {
      const tr = document.createElement("tr");

      // Shift indicator: was this question moved?
      const diff = m.new_number - m.original_number;
      let shiftHtml = "";
      if (diff > 0) {
        shiftHtml = `<span class="shift-indicator shift-down" title="Đã chuyển xuống ${diff} vị trí so với gốc">▼ Câu ${m.original_number}</span>`;
      } else if (diff < 0) {
        shiftHtml = `<span class="shift-indicator shift-up" title="Đã chuyển lên ${Math.abs(diff)} vị trí so với gốc">▲ Câu ${m.original_number}</span>`;
      } else {
        shiftHtml = `<span class="shift-indicator shift-same" title="Giữ nguyên vị trí ban đầu">Giữ nguyên</span>`;
      }

      // Check if answer changed due to option shuffle
      let ansHtml = "";
      if (isTeacher) {
        const isAnsChanged = m.original_answer && m.new_answer && m.original_answer !== m.new_answer;
        const note = isAnsChanged ? `<small style="display:block; font-size:0.75rem; color:#64748b;">(Đổi từ ${m.original_answer})</small>` : "";
        ansHtml = `
          <td class="col-answer" style="font-weight:600; color:#64748b;">${m.original_answer || "-"}</td>
          <td class="col-answer" style="font-weight:700; color:#059669; font-size:1rem;">
            ${m.new_answer || "-"}
            ${note}
          </td>
        `;
      } else {
        ansHtml = "";
      }

      tr.innerHTML = `
        <td style="font-weight:700; color:#2563eb; font-size:0.95rem;">
          Câu ${m.new_number}
        </td>
        <td>
          <span class="badge-orig-q">Câu gốc ${m.original_number}</span>
          ${shiftHtml}
        </td>
        ${ansHtml}
        <td style="color:#334155; font-size:0.85rem; line-height:1.4;">${m.lead_preview}</td>
      `;
      tbody.appendChild(tr);
    });
  },

  renderPositionMatrix() {
    if (!this.analysis || !this.analysis.questions) return;
    const codes = Object.keys(this.variants);
    if (codes.length === 0) return;

    const thead = document.getElementById("allVariantsMatrixHead");
    const tbody = document.getElementById("allVariantsMatrixBody");

    // Build thead
    let headHtml = `
      <tr>
        <th style="width: 100px;">Câu gốc</th>
        <th style="text-align:left;">Nội dung câu hỏi đề gốc</th>
        <th style="width: 90px;">Đ/A gốc</th>
    `;
    codes.forEach((code) => {
      headHtml += `<th style="width: 110px;">Mã ${code}</th>`;
    });
    headHtml += `</tr>`;
    thead.innerHTML = headHtml;

    // Build tbody
    tbody.innerHTML = "";
    this.analysis.questions.forEach((q) => {
      const tr = document.createElement("tr");
      const origNum = q.original_number;
      const origAns = this.customAnswers[`q_${origNum}`] || q.correct_answer || this.analysis.detected_answers[origNum] || "-";

      let rowHtml = `
        <td style="font-weight:700; color:#475569;">Câu ${origNum}</td>
        <td style="text-align:left; font-size:0.85rem; color:#334155;">${q.lead_text ? q.lead_text.substring(0, 65) : "Câu hỏi " + origNum}...</td>
        <td style="font-weight:600; color:#64748b;">${origAns}</td>
      `;

      codes.forEach((code) => {
        const varData = this.variants[code];
        const mapping = varData ? varData.question_mappings.find((m) => m.original_number === origNum) : null;
        if (mapping) {
          rowHtml += `
            <td>
              <span class="matrix-cell-pos">Câu ${mapping.new_number}</span>
              <div style="font-size:0.75rem; color:#059669; font-weight:600; margin-top:2px;">
                Đ/A: ${mapping.new_answer || "-"}
              </div>
            </td>
          `;
        } else {
          rowHtml += `<td>-</td>`;
        }
      });

      tr.innerHTML = rowHtml;
      tbody.appendChild(tr);
    });
  },

  renderStep6() {
    const list = document.getElementById("individualDownloadsList");
    list.innerHTML = "";

    Object.keys(this.variants).forEach((code) => {
      const card = document.createElement("div");
      card.className = "variant-card";
      card.innerHTML = `
        <div class="variant-card-header">
          <div class="variant-card-code">Mã đề: ${code}</div>
          <span class="badge-tag" style="background:#eff6ff; color:#2563eb; font-size:0.75rem;">
            Đã xáo chuẩn
          </span>
        </div>
        <p style="font-size:0.82rem; color:var(--text-muted); margin-bottom:1rem; flex-grow:1;">
          Tùy chọn tải riêng cho mã ${code}: phát cho học sinh làm bài hoặc bản lưu cho giáo viên chấm thi.
        </p>
        <div class="variant-card-actions">
          <button type="button" class="btn-card-action btn-card-student" onclick="app.downloadVariant('${code}', 'student')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
            📄 Chỉ đề thi (Học sinh)
          </button>
          <button type="button" class="btn-card-action btn-card-teacher" onclick="app.downloadVariant('${code}', 'teacher')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
            📑 Kèm đáp án & đối chiếu (GV)
          </button>
        </div>
      `;
      list.appendChild(card);
    });
  },

  downloadActiveVariant(mode) {
    if (!this.activePreviewCode) return;
    this.downloadVariant(this.activePreviewCode, mode);
  },

  triggerDownload(url, filename) {
    const a = document.createElement("a");
    a.href = url;
    if (filename) {
      a.setAttribute("download", filename);
    }
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      if (a.parentNode) {
        a.parentNode.removeChild(a);
      }
    }, 200);
  },

  downloadVariant(code, mode = null) {
    if (!this.sessionId) return;
    if (!mode) {
      this.openExportChoiceModal(code);
      return;
    }
    const rawName = (this.analysis && this.analysis.filename) ? this.analysis.filename : "De_Thi";
    const baseName = rawName.substring(0, rawName.lastIndexOf('.')) || rawName;
    const cleanBase = baseName.replace(/[^a-zA-Z0-9_.-]/g, "_");
    const suffix = (mode === "teacher" || mode === "with_answers") ? "_Kem_Dap_An" : "";
    const filename = `${cleanBase}_De_${code}${suffix}.docx`;
    const url = `/api/download/${this.sessionId}/${code}/${encodeURIComponent(filename)}?mode=${mode}`;
    this.triggerDownload(url, filename);
  },

  downloadZip(mode = "all") {
    if (!this.sessionId) return;
    const rawName = (this.analysis && this.analysis.filename) ? this.analysis.filename : "De_Thi";
    const baseName = rawName.substring(0, rawName.lastIndexOf('.')) || rawName;
    const cleanBase = baseName.replace(/[^a-zA-Z0-9_.-]/g, "_");
    const suffix = (mode === "student" || mode === "exam_only") ? "_Hoc_Sinh" : ((mode === "teacher" || mode === "with_answers") ? "_Giao_Vien" : "");
    const filename = `${cleanBase}_Bo_De_Thi${suffix}.zip`;
    const url = `/api/download-zip/${this.sessionId}/${encodeURIComponent(filename)}?mode=${mode}`;
    this.triggerDownload(url, filename);
  },

  downloadExcel() {
    if (!this.sessionId) return;
    const filename = "Bang_Anh_Xa_Va_Dap_An.xlsx";
    const url = `/api/download-excel/${this.sessionId}/${encodeURIComponent(filename)}`;
    this.triggerDownload(url, filename);
  },

  downloadAnswerDocx() {
    if (!this.sessionId) return;
    const filename = "Bang_Dap_An_Tong_Hop.docx";
    const url = `/api/download-answer-docx/${this.sessionId}/${encodeURIComponent(filename)}`;
    this.triggerDownload(url, filename);
  },

  openExportChoiceModal(code) {
    this.exportTargetCode = code;
    document.getElementById("exportModalTitle").textContent = `Tùy chọn xuất: Đề thi Mã ${code}`;
    this.selectModalExportOption("student");
    document.getElementById("exportChoiceModal").classList.add("active");
  },

  closeExportChoiceModal() {
    document.getElementById("exportChoiceModal").classList.remove("active");
    this.exportTargetCode = null;
  },

  selectModalExportOption(option) {
    this.exportModalSelectedOption = option;
    const cardStudent = document.getElementById("optCardStudent");
    const cardTeacher = document.getElementById("optCardTeacher");
    const radioStudent = document.getElementById("radioOptStudent");
    const radioTeacher = document.getElementById("radioOptTeacher");

    if (option === "teacher") {
      cardStudent.classList.remove("active");
      cardTeacher.classList.add("active");
      radioTeacher.checked = true;
    } else {
      cardTeacher.classList.remove("active");
      cardStudent.classList.add("active");
      radioStudent.checked = true;
    }
  },

  confirmExportModalAction() {
    if (!this.exportTargetCode) return;
    const mode = this.exportModalSelectedOption;
    const code = this.exportTargetCode;
    this.closeExportChoiceModal();
    this.downloadVariant(code, mode);
  },

  resetAll() {
    if (confirm("Thầy/Cô có muốn nạp một đề thi mới?")) {
      window.location.reload();
    }
  },
};

// Initialize when DOM ready
document.addEventListener("DOMContentLoaded", () => {
  app.init();
  document.getElementById("btnResetApp").addEventListener("click", () => app.resetAll());
});
