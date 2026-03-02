let spProfiles = [];
let spCurrentProfileId = null;
let spCurrentType = "individual";
let spIsDirty = false;
let spAddressActiveField = "reg"; // reg | residence | legal_rf
const spSteps = ["main", "docs", "address", "contacts", "bank"];

function spCurrentStepIndex() {
  return spSteps.findIndex((key) =>
    document.getElementById("tab-" + key)?.classList.contains("active")
  );
}

function spSetStep(stepIndex) {
  spSteps.forEach((key, index) => {
    const tab = document.getElementById("tab-" + key);
    const pane = document.getElementById("pane-" + key);
    if (!tab || !pane) return;
    if (index === stepIndex) {
      tab.classList.add("active");
      pane.classList.add("show", "fade", "active");
    } else {
      tab.classList.remove("active");
      pane.classList.remove("show", "active");
    }
  });
  const prevBtn = document.getElementById("spWizardPrev");
  if (prevBtn) prevBtn.disabled = stepIndex === 0;
  const saveVisible = stepIndex >= 1;
  const nextBtn = document.getElementById("spWizardNext");
  const saveBtn = document.getElementById("spWizardSave");
  const saveCloseBtn = document.getElementById("spWizardSaveClose");
  if (nextBtn) nextBtn.classList.toggle("d-none", saveVisible);
  if (saveBtn) saveBtn.classList.toggle("d-none", !saveVisible);
  if (saveCloseBtn) saveCloseBtn.classList.toggle("d-none", !saveVisible);
  const stepLabel = document.getElementById("spWizardStepLabel");
  if (stepLabel) {
    stepLabel.textContent = `Шаг ${stepIndex + 1} из ${spSteps.length}`;
  }
  spUpdateSaveButtonsState();
}

function spWizardPrev() {
  const activeIndex = spCurrentStepIndex();
  if (activeIndex > 0) spSetStep(activeIndex - 1);
}

function spWizardNext() {
  const activeIndex = spCurrentStepIndex();
  if (activeIndex < spSteps.length - 1) spSetStep(activeIndex + 1);
}

function spUpdateTypeVisibility() {
  const isInd = spCurrentType === "individual";
  const isLegal = spCurrentType === "legal";
  const isSP = spCurrentType === "sole_proprietor";

  const label = document.getElementById("spProfileTypeLabel");
  if (label) {
    label.textContent = isInd
      ? "Физическое лицо"
      : isLegal
      ? "Юридическое лицо"
      : "Индивидуальный предприниматель";
  }

  ["spMainFieldsIndividual", "spDocsIndividual", "spAddressIndividual"].forEach(
    (id) => {
      const el = document.getElementById(id);
      if (el) el.classList.toggle("d-none", !isInd);
    }
  );
  ["spMainFieldsLegal", "spDocsLegal", "spAddressLegal"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle("d-none", !isLegal);
  });
  ["spMainFieldsSP", "spDocsSP", "spAddressSP"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle("d-none", !isSP);
  });

  const typeMap = {
    individual: "spTypeIndividual",
    sole_proprietor: "spTypeSP",
    legal: "spTypeLegal",
  };
  Object.entries(typeMap).forEach(([t, id]) => {
    const radio = document.getElementById(id);
    if (radio) radio.checked = spCurrentType === t;
  });
}

function spChangeType(newType) {
  spCurrentType = newType || "individual";
  spUpdateTypeVisibility();
  spMarkDirty();
}

function spOpenProfileWizard(type, existingProfile = null) {
  spCurrentType = type || "individual";
  spCurrentProfileId = existingProfile ? existingProfile.id : null;

  const card = document.getElementById("spProfileEditorCard");
  if (card) {
    card.style.display = "flex";
  }

  const title = document.getElementById("spEditorTitle");
  const subtitle = document.getElementById("spEditorSubtitle");
  const verifiedBadge = document.getElementById("spProfileVerifiedBadge");

  const form = document.getElementById("spProfileForm");
  if (form) {
    form.reset();
  }
  spIsDirty = false;
  spUpdateSaveButtonsState();

  if (existingProfile) {
    if (title) title.textContent = "Редактирование профиля";
    if (subtitle) subtitle.textContent = existingProfile.display_name || "";
    const isVerified = !!existingProfile.is_verified;
    if (verifiedBadge) {
      verifiedBadge.classList.toggle("d-none", !isVerified);
    }
    const kycBtn = document.getElementById("spStartKycBtn");
    if (kycBtn) {
      kycBtn.classList.toggle("d-none", isVerified);
    }
    spCurrentType = existingProfile.profile_type || spCurrentType;
  } else {
    if (title) title.textContent = "Новый профиль";
    if (subtitle) subtitle.textContent = "";
    if (verifiedBadge) verifiedBadge.classList.add("d-none");
    const kycBtn = document.getElementById("spStartKycBtn");
    if (kycBtn) {
      kycBtn.classList.remove("d-none");
    }
  }

  spUpdateTypeVisibility();
  spSetStep(0);

  if (existingProfile && existingProfile.details) {
    spFillFormFromDetails(existingProfile);
  }

  // Пытаемся восстановить черновик, если он есть
  if (spRestoreAutosave()) {
    spIsDirty = true;
    spUpdateSaveButtonsState();
  }
}

function spFillFormFromDetails(profile) {
  const details = profile.details || {};
  const form = document.getElementById("spProfileForm");
  const displayNameInput = document.getElementById("spDisplayName");
  if (displayNameInput) {
    displayNameInput.value = profile.display_name || "";
  }

  Object.keys(details).forEach((key) => {
    let el = null;
    if (spCurrentType === "individual") {
      el = document.querySelector(
        '#spMainFieldsIndividual [name="' +
          key +
          '"], #spDocsIndividual [name="' +
          key +
          '"]'
      );
    } else if (spCurrentType === "legal") {
      el = document.querySelector(
        '#spMainFieldsLegal [name="' +
          key +
          '"], #spDocsLegal [name="' +
          key +
          '"]'
      );
    } else if (spCurrentType === "sole_proprietor") {
      el = document.querySelector(
        '#spMainFieldsSP [name="' + key + '"], #spDocsSP [name="' + key + '"]'
      );
    }
    if (!el && form) {
      el = form.querySelector('[name="' + key + '"]');
    }
    if (!el || details[key] === null || typeof details[key] === "undefined")
      return;
    if (el.type === "checkbox") {
      el.checked = !!details[key];
    } else if (el.type === "date") {
      const dateValue = details[key];
      if (dateValue && typeof dateValue === "string") {
        el.value = dateValue.split("T")[0];
      } else {
        el.value = dateValue || "";
      }
    } else {
      el.value = details[key];
    }
  });

  if (spCurrentType === "individual") {
    const regId = details.registration_address_id;
    const regFull = details.registration_address_full || "";
    const resId = details.residence_address_id;
    const resFull = details.residence_address_full || "";

    const regIdInput = document.getElementById("spRegAddressId");
    const regTextInput = document.getElementById("spRegAddressText");
    const searchInput = document.getElementById("spAddressSearchInput");
    const resIdInput = document.getElementById("spResidenceAddressId");
    const resDisplay =
      document.getElementById("spResidenceAddressDisplayInd") ||
      document.getElementById("spResidenceAddressDisplay");
    const sameCheckbox = document.getElementById("spSameAsReg");
    const residenceBlock = document.getElementById(
      "spAddressIndividualResidence"
    );

    if (regIdInput) regIdInput.value = regId || "";
    if (regTextInput) regTextInput.value = regFull;
    if (searchInput) searchInput.value = regFull;
    if (resIdInput) resIdInput.value = resId || "";

    if (sameCheckbox && residenceBlock && resFull && regFull && resFull !== regFull) {
      sameCheckbox.checked = false;
      residenceBlock.style.display = "block";
      if (resDisplay) resDisplay.value = resFull;
    } else {
      if (sameCheckbox && residenceBlock) {
        sameCheckbox.checked = true;
        residenceBlock.style.display = "none";
      }
      if (resDisplay) resDisplay.value = resFull || regFull || "";
    }

    if (window.SPAddressMap && SPAddressMap.setCenterByQuery && regFull) {
      SPAddressMap.setCenterByQuery(regFull);
    }
  } else if (spCurrentType === "legal") {
    const regId = details.registration_address_id;
    const regFull = details.registration_address_full || "";
    const rfId = details.address_rf_id;
    const rfFull = details.address_rf_full || "";

    const regIdInput = document.getElementById("spLegalRegAddressId");
    const searchInput = document.getElementById("spAddressSearchInput");
    const rfIdInput = document.getElementById("spLegalAddressId");
    const rfDisplay = document.getElementById("spLegalAddressDisplay");
    const sameCheckbox = document.getElementById("spLegalSameAsReg");
    const rfBlock = document.getElementById("spAddressLegalRF");

    if (!regId && !regFull && rfFull) {
      if (regIdInput) regIdInput.value = "";
      if (searchInput) searchInput.value = "";
      if (rfIdInput) rfIdInput.value = rfId || "";
      if (rfDisplay) rfDisplay.value = rfFull;
      if (sameCheckbox && rfBlock) {
        sameCheckbox.checked = false;
        rfBlock.style.display = "block";
      }
    } else {
      if (regIdInput) regIdInput.value = regId || "";
      if (searchInput) searchInput.value = regFull;
      if (rfIdInput) rfIdInput.value = rfId || "";

      if (sameCheckbox && rfBlock && rfFull && regFull && rfFull !== regFull) {
        sameCheckbox.checked = false;
        rfBlock.style.display = "block";
        if (rfDisplay) rfDisplay.value = rfFull;
      } else {
        if (sameCheckbox && rfBlock) {
          sameCheckbox.checked = true;
          rfBlock.style.display = "none";
        }
        if (rfDisplay) rfDisplay.value = rfFull || regFull || "";
      }
    }

    if (window.SPAddressMap && SPAddressMap.setCenterByQuery && regFull) {
      SPAddressMap.setCenterByQuery(regFull);
    }

    const repProfileId =
      details.representative_profile_profile_id || details.representative_profile_id;
    const repDisplay = document.getElementById("spRepresentativeDisplay");
    const repIdInput = document.getElementById("spRepresentativeId");
    if (repProfileId) {
      if (repIdInput && details.representative_profile_id) {
        repIdInput.value = details.representative_profile_id;
      }
      const repProfile = spProfiles.find((p) => p.id === repProfileId);
      if (repDisplay) {
        repDisplay.value = repProfile
          ? repProfile.display_name
          : `Профиль #${repProfileId}`;
      }
    } else {
      if (repIdInput) repIdInput.value = "";
      if (repDisplay) repDisplay.value = "";
    }
  } else if (spCurrentType === "sole_proprietor") {
    const resId = details.residence_address_id;
    const resFull = details.residence_address_full || "";
    const resIdInput = document.getElementById("spResidenceAddressId");
    if (resIdInput) resIdInput.value = resId || "";
    const addrInput = document.getElementById("spAddressSearchInput");
    if (addrInput) {
      addrInput.value = resFull || "";
    }
    if (window.SPAddressMap && SPAddressMap.setCenterByQuery && resFull) {
      SPAddressMap.setCenterByQuery(resFull);
    }
  }
}

async function spLoadProfiles() {
  try {
    const resp = await fetch("/api/profiles/");
    const data = await resp.json();
    if (!data.success) return;
    spProfiles = data.profiles || [];
    const countEl = document.getElementById("spProfilesCount");
    if (countEl) countEl.textContent = spProfiles.length;
    const list = document.getElementById("spProfilesList");
    if (!list) return;
    list.innerHTML = "";

    const createItem = document.createElement("button");
    createItem.type = "button";
    createItem.className =
      "list-group-item list-group-item-action d-flex justify-content-between align-items-center";
    createItem.onclick = () => spCreateNewProfileFromList();
    createItem.innerHTML = `
      <div>
        <div class="fw-semibold text-primary">
          <i class="bi bi-plus-circle me-1"></i>
          Создать новый профиль
        </div>
        <div class="small text-muted">Выберите тип профиля и заполните данные</div>
      </div>
    `;
    list.appendChild(createItem);

    spProfiles.forEach((p) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className =
        "list-group-item list-group-item-action d-flex justify-content-between align-items-center";
      const typeLabel =
        p.profile_type === "individual"
          ? "ФЛ"
          : p.profile_type === "legal"
          ? "ЮЛ"
          : "ИП";
      item.innerHTML = `
        <div>
          <div class="fw-semibold">${p.display_name}</div>
          <div class="small text-muted">${typeLabel}</div>
        </div>
        <div class="text-end">
          ${p.is_default ? '<span class="badge bg-primary mb-1">По умолчанию</span><br>' : ""}
          ${p.is_verified ? '<span class="badge bg-success">KYC</span>' : ""}
        </div>
      `;
      item.onclick = () => spEditProfileFromList(p.id);
      list.appendChild(item);
    });
  } catch (e) {
    console.error("Load profiles error", e);
  }
}

async function spEditProfileFromList(id) {
  const profile = spProfiles.find((p) => p.id === id);
  if (!profile) return;
  spCurrentType = profile.profile_type;
  spOpenProfileWizard(spCurrentType, profile);
}

async function spSaveProfile(closeAfter) {
  const form = document.getElementById("spProfileForm");
  if (!form) return;
  const fd = new FormData(form);
  const displayName = (fd.get("display_name") || "").toString().trim();
  if (!displayName) {
    spSetStep(0);
    setTimeout(() => {
      const el = document.getElementById("spDisplayName");
      if (el) { el.focus(); el.reportValidity(); }
    }, 100);
    return;
  }
  const payload = {
    profile_type: spCurrentType,
    display_name: displayName,
  };

  if (spCurrentType === "individual") {
    const sameCheckbox = document.getElementById("spSameAsReg");
    const regIdInput = document.getElementById("spRegAddressId");
    const resIdInput = document.getElementById("spResidenceAddressId");
    if (sameCheckbox && sameCheckbox.checked && regIdInput && resIdInput) {
      resIdInput.value = regIdInput.value;
    }
  }

  if (spCurrentType === "legal") {
    const sameCheckbox = document.getElementById("spLegalSameAsReg");
    const regIdInput = document.getElementById("spLegalRegAddressId");
    const rfIdInput = document.getElementById("spLegalAddressId");
    if (sameCheckbox && sameCheckbox.checked && regIdInput && rfIdInput) {
      rfIdInput.value = regIdInput.value;
    }
  }

  const dateFields = ["ogrn_assigned_at", "passport_issued_at", "birth_date"];
  const hiddenFields = [
    "registration_address_id",
    "residence_address_id",
    "address_rf_id",
    "representative_profile_id",
  ];

  dateFields.forEach((key) => {
    let el = null;
    if (spCurrentType === "legal" && key === "ogrn_assigned_at") {
      el = form.querySelector('#spDocsLegal [name="ogrn_assigned_at"]');
    } else if (spCurrentType === "individual") {
      if (key === "passport_issued_at") {
        el = form.querySelector('#spDocsIndividual [name="passport_issued_at"]');
      } else if (key === "birth_date") {
        el = form.querySelector('#spMainFieldsIndividual [name="birth_date"]');
      }
    }
    if (!el) {
      el = form.querySelector('[name="' + key + '"]');
    }
    if (el) {
      payload[key] = el.value || "";
    }
  });

  hiddenFields.forEach((key) => {
    let elId = null;
    if (key === "registration_address_id") {
      if (spCurrentType === "legal") {
        elId = "spLegalRegAddressId";
      } else if (spCurrentType === "individual") {
        elId = "spRegAddressId";
      }
    } else if (key === "address_rf_id") {
      elId = "spLegalAddressId";
    } else if (key === "residence_address_id") {
      elId = "spResidenceAddressId";
    } else if (key === "representative_profile_id") {
      elId = "spRepresentativeId";
    }
    if (elId) {
      const el = document.getElementById(elId);
      if (el) {
        payload[key] = el.value || "";
      }
    }
  });

  fd.forEach((value, key) => {
    if (key === "display_name") return;
    if (dateFields.includes(key) || hiddenFields.includes(key)) {
      return;
    }
    if (!value) return;
    if (key === "is_self_employed") {
      payload[key] = true;
    } else {
      payload[key] = String(value);
    }
  });

  try {
    const url = spCurrentProfileId
      ? `/api/profiles/${spCurrentProfileId}`
      : "/api/profiles/";
    const method = spCurrentProfileId ? "PUT" : "POST";
    const resp = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!resp.ok || !data.success) {
      alert(data.detail || data.error || "Ошибка сохранения профиля");
      return;
    }
    spCurrentProfileId = (data.profile && data.profile.id) || spCurrentProfileId;
    await spLoadProfiles();
    if (spCurrentProfileId) {
      const updatedProfile = spProfiles.find((p) => p.id === spCurrentProfileId);
      if (updatedProfile && updatedProfile.display_name) {
        const subtitle = document.getElementById("spEditorSubtitle");
        if (subtitle) subtitle.textContent = updatedProfile.display_name;
        const displayNameInput = document.getElementById("spDisplayName");
        if (displayNameInput)
          displayNameInput.value = updatedProfile.display_name;
      }
    }
    spIsDirty = false;
    spUpdateSaveButtonsState();
    spClearAutosave();
    if (closeAfter) {
      const target = typeof spCloseRedirectUrl !== "undefined"
        ? spCloseRedirectUrl
        : "/owner/profile?success=1";
      window.location.href = target;
    } else {
      alert("Профиль сохранен");
    }
  } catch (e) {
    console.error("Save profile error", e);
    alert("Ошибка сохранения профиля");
  }
}

function spOnRegistrationAddressSelected(addr) {
  const regIdInput = document.getElementById("spRegAddressId");
  if (regIdInput) regIdInput.value = addr.id;
  const regTextInput = document.getElementById("spRegAddressText");
  if (regTextInput) {
    regTextInput.value = addr.full_address || "";
  }
  const searchInput = document.getElementById("spAddressSearchInput");
  if (searchInput) {
    searchInput.value = addr.full_address || "";
  }
  spMarkDirty();
}

function spOnLegalRegAddressSelected(addr) {
  const regIdInput = document.getElementById("spLegalRegAddressId");
  const searchInput = document.getElementById("spAddressSearchInput");
  if (regIdInput) regIdInput.value = addr.id;
  if (searchInput) searchInput.value = addr.full_address || "";
  spMarkDirty();
}

function spOnLegalRfAddressSelected(addr) {
  const rfIdInput = document.getElementById("spLegalAddressId");
  const rfDisplay = document.getElementById("spLegalAddressDisplay");
  const searchInput = document.getElementById("spAddressSearchInput");
  if (rfIdInput) rfIdInput.value = addr.id;
  if (rfDisplay) rfDisplay.value = addr.full_address || "";
  if (searchInput) searchInput.value = addr.full_address || "";
  spMarkDirty();
}

function spOnLegalAddressSelected(addr) {
  const sameCheckbox = document.getElementById("spLegalSameAsReg");
  if (spAddressActiveField === "legal_rf" && sameCheckbox && !sameCheckbox.checked) {
    spOnLegalRfAddressSelected(addr);
  } else {
    spOnLegalRegAddressSelected(addr);
    if (sameCheckbox && sameCheckbox.checked) {
      spOnLegalRfAddressSelected(addr);
    }
  }
}

function spOnResidenceAddressSelected(addr) {
  const resIdInput = document.getElementById("spResidenceAddressId");
  if (resIdInput) resIdInput.value = addr.id;
  const input =
    document.getElementById("spResidenceAddressDisplayInd") ||
    document.getElementById("spResidenceAddressDisplay");
  if (input) {
    input.value = addr.full_address || "";
  }
  spMarkDirty();
}

function spSelectRepresentative() {
  const individualProfiles = spProfiles.filter((p) => p.profile_type === "individual");
  if (individualProfiles.length === 0) {
    alert("Нет доступных профилей физических лиц. Сначала создайте профиль ФЛ.");
    return;
  }
  const modalHtml = `
    <div class="modal fade" id="spSelectRepresentativeModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Выбор представителя</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="list-group">
              ${individualProfiles
                .map(
                  (p) => `
                <button type="button" class="list-group-item list-group-item-action" onclick="spSetRepresentative(${p.id}, '${(p.details?.last_name || "")} ${(p.details?.first_name || "")} ${(p.details?.middle_name || "")}'.trim() || '${p.display_name}')">
                  <div class="fw-semibold">${p.display_name}</div>
                  <div class="small text-muted">ID профиля: ${p.id}</div>
                </button>
              `
                )
                .join("")}
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
            <button type="button" class="btn btn-outline-danger" onclick="spClearRepresentative()">Очистить</button>
          </div>
        </div>
      </div>
    </div>
  `;
  const oldModal = document.getElementById("spSelectRepresentativeModal");
  if (oldModal) {
    oldModal.remove();
  }
  document.body.insertAdjacentHTML("beforeend", modalHtml);
  const modalEl = document.getElementById("spSelectRepresentativeModal");
  if (!modalEl || typeof bootstrap === "undefined") return;
  const modal = new bootstrap.Modal(modalEl);
  modal.show();
  modalEl.addEventListener("hidden.bs.modal", function () {
    this.remove();
  });
}

function spSetRepresentative(profileId, displayName) {
  const idInput = document.getElementById("spRepresentativeId");
  const displayInput = document.getElementById("spRepresentativeDisplay");
  if (idInput) idInput.value = profileId;
  if (displayInput) {
    displayInput.value = displayName || `Профиль #${profileId}`;
  }
  const modalEl = document.getElementById("spSelectRepresentativeModal");
  if (modalEl && typeof bootstrap !== "undefined") {
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
  }
  spMarkDirty();
}

function spClearRepresentative() {
  const idInput = document.getElementById("spRepresentativeId");
  const displayInput = document.getElementById("spRepresentativeDisplay");
  if (idInput) idInput.value = "";
  if (displayInput) displayInput.value = "";
  const modalEl = document.getElementById("spSelectRepresentativeModal");
  if (modalEl && typeof bootstrap !== "undefined") {
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
  }
  spMarkDirty();
}

async function spStartKyc() {
  if (!spCurrentProfileId) {
    alert("Сначала выберите или создайте профиль.");
    return;
  }
  const btn = document.getElementById("spStartKycBtn");
  try {
    if (btn) btn.disabled = true;
    const resp = await fetch(
      `/api/profiles/${spCurrentProfileId}/kyc/start`,
      { method: "POST" }
    );
    const data = await resp.json();
    if (!data.success) {
      alert(data.error || "Не удалось запустить проверку KYC");
      if (btn) btn.disabled = false;
      return;
    }
    const respVerify = await fetch(
      `/api/profiles/${spCurrentProfileId}/kyc/mark-verified`,
      { method: "POST" }
    );
    const verifyData = await respVerify.json();
    if (!verifyData.success) {
      alert(verifyData.error || "Ошибка при подтверждении профиля");
    } else {
      alert("Профиль подтвержден через KYC.");
      const badge = document.getElementById("spProfileVerifiedBadge");
      if (badge) badge.classList.remove("d-none");
      if (btn) btn.classList.add("d-none");
      await spLoadProfiles();
    }
  } catch (e) {
    console.error("KYC start error", e);
    alert("Ошибка запуска KYC‑верификации");
  } finally {
    if (btn) btn.disabled = false;
  }
}

function spUpdateSaveButtonsState() {
  const saveBtn = document.getElementById("spWizardSave");
  const saveCloseBtn = document.getElementById("spWizardSaveClose");
  const stepIdx = spCurrentStepIndex();
  const enabled = stepIdx >= 1;
  if (saveBtn) saveBtn.disabled = !enabled;
  if (saveCloseBtn) saveCloseBtn.disabled = !enabled;
}

function spMarkDirty() {
  spIsDirty = true;
  spUpdateSaveButtonsState();
}

function spBindDirtyHandlers() {
  const form = document.getElementById("spProfileForm");
  if (!form) return;
  form.addEventListener("input", spMarkDirty);
  form.addEventListener("change", spMarkDirty);
}

function spBindTabHandlers() {
  spSteps.forEach((key, index) => {
    const tab = document.getElementById("tab-" + key);
    if (!tab) return;
    tab.addEventListener("click", function () {
      spSetStep(index);
    });
  });
}

function spBindAddressFocusHandlers() {
  const searchInput = document.getElementById("spAddressSearchInput");
  const resInput =
    document.getElementById("spResidenceAddressDisplayInd") ||
    document.getElementById("spResidenceAddressDisplay");
  const sameCheckbox = document.getElementById("spSameAsReg");
  const residenceBlock = document.getElementById("spAddressIndividualResidence");
  const addrLabel = document.querySelector("label[for='spAddressSearchInput']");
  const legalSameCheckbox = document.getElementById("spLegalSameAsReg");
  const legalRfBlock = document.getElementById("spAddressLegalRF");
  const legalRfInput = document.getElementById("spLegalAddressDisplay");

  if (sameCheckbox && residenceBlock) {
    sameCheckbox.addEventListener("change", function () {
      if (this.checked) {
        residenceBlock.style.display = "none";
        if (addrLabel) {
          addrLabel.textContent = "Адрес регистрации";
        }
        const searchInput = document.getElementById("spAddressSearchInput");
        const regTextInput = document.getElementById("spRegAddressText");
        if (searchInput && regTextInput) {
          searchInput.value = regTextInput.value || "";
          if (
            window.SPAddressMap &&
            SPAddressMap.setCenterByQuery &&
            regTextInput.value
          ) {
            SPAddressMap.setCenterByQuery(regTextInput.value);
          }
        }
        spAddressActiveField = "reg";
      } else {
        residenceBlock.style.display = "block";
        const searchInput = document.getElementById("spAddressSearchInput");
        if (resInput && !resInput.value && searchInput) {
          resInput.value = searchInput.value;
        }
        if (addrLabel) {
          addrLabel.textContent = "Адрес проживания";
        }
        if (resInput) {
          resInput.focus();
        }
        spAddressActiveField = "residence";
      }
      spMarkDirty();
    });
  }

  if (searchInput) {
    searchInput.addEventListener("focus", function () {
      spAddressActiveField = "reg";
      if (window.SPAddressMap && SPAddressMap.setCenterByQuery) {
        const q = this.value.trim();
        if (q) SPAddressMap.setCenterByQuery(q);
      }
    });
  }

  if (resInput) {
    resInput.addEventListener("focus", function () {
      spAddressActiveField = "residence";
      if (window.SPAddressMap && SPAddressMap.setCenterByQuery) {
        const q = this.value.trim();
        if (q) SPAddressMap.setCenterByQuery(q);
      }
    });

    resInput.addEventListener("input", function () {
      const sInput = document.getElementById("spAddressSearchInput");
      if (sInput) {
        sInput.value = this.value;
        const evt = new Event("input", { bubbles: true });
        sInput.dispatchEvent(evt);
      }
    });
  }

  if (legalSameCheckbox && legalRfBlock) {
    legalSameCheckbox.addEventListener("change", function () {
      if (this.checked) {
        legalRfBlock.style.display = "none";
        spAddressActiveField = "reg";
      } else {
        legalRfBlock.style.display = "block";
        if (legalRfInput) {
          legalRfInput.focus();
        }
        spAddressActiveField = "legal_rf";
      }
      spMarkDirty();
    });
  }

  if (legalRfInput) {
    legalRfInput.addEventListener("focus", function () {
      spAddressActiveField = "legal_rf";
      if (window.SPAddressMap && SPAddressMap.setCenterByQuery) {
        const q = this.value.trim();
        if (q) SPAddressMap.setCenterByQuery(q);
      }
    });
    legalRfInput.addEventListener("input", function () {
      const sInput = document.getElementById("spAddressSearchInput");
      if (sInput) {
        sInput.value = this.value;
        const evt = new Event("input", { bubbles: true });
        sInput.dispatchEvent(evt);
      }
    });
  }
}

function spCreateNewProfileFromList() {
  spOpenProfileWizard("individual", null);
}

document.addEventListener("DOMContentLoaded", function () {
  if (typeof SPAddressMap !== "undefined" && SPAddressMap && SPAddressMap.init) {
    const addrLabel = document.querySelector("label[for='spAddressSearchInput']");
    if (addrLabel) {
      addrLabel.textContent = "Адрес регистрации";
    }
    SPAddressMap.init({
      searchInputId: "spAddressSearchInput",
      suggestionsId: "spAddressSuggestions",
      mapContainerId: "spAddressMap",
      onAddressSelected: async function (addrDto) {
        try {
          const payload = {
            full_address: addrDto.full_address,
            city: addrDto.city || "",
          };
          const resp = await fetch("/api/addresses/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          const data = await resp.json();
          if (!data.success) {
            console.error("Address create error", data.error);
            return;
          }
          const address = data.address;
          if (spCurrentType === "individual") {
            const sameCheckbox = document.getElementById("spSameAsReg");
            if (spAddressActiveField === "residence" && sameCheckbox && !sameCheckbox.checked) {
              spOnResidenceAddressSelected(address);
            } else {
              spOnRegistrationAddressSelected(address);
              if (sameCheckbox && sameCheckbox.checked) {
                spOnResidenceAddressSelected(address);
              }
            }
          } else if (spCurrentType === "legal") {
            spOnLegalAddressSelected(address);
          } else if (spCurrentType === "sole_proprietor") {
            spOnResidenceAddressSelected(address);
          }
        } catch (e) {
          console.error("Address create error", e);
        }
      },
    });
  }

  spBindDirtyHandlers();
  spBindTabHandlers();
  spBindAddressFocusHandlers();
  spInitAutosave();

  spLoadProfiles().then(function () {
    if (typeof spSelectedProfileId !== "undefined" && spSelectedProfileId) {
      const id = parseInt(spSelectedProfileId, 10);
      if (!Number.isNaN(id)) {
        spEditProfileFromList(id);
      }
    }
  });
});


// ─── Автосохранение в localStorage ───────────────────────────

function _spAutosaveKey() {
  return "profile_draft_" + (spCurrentProfileId || "new") + "_" + spCurrentType;
}

let _spAutosaveTimer = null;

function _spAutosaveToStorage() {
  const form = document.getElementById("spProfileForm");
  if (!form) return;
  const data = {};
  new FormData(form).forEach(function (val, key) {
    data[key] = val;
  });
  data._step = spCurrentStepIndex();
  data._type = spCurrentType;
  try {
    localStorage.setItem(_spAutosaveKey(), JSON.stringify(data));
    _spShowAutosaveIndicator();
  } catch (e) { /* quota exceeded */ }
}

function _spShowAutosaveIndicator() {
  let el = document.getElementById("spAutosaveStatus");
  if (!el) {
    el = document.createElement("span");
    el.id = "spAutosaveStatus";
    el.className = "text-muted small ms-2";
    const stepLabel = document.getElementById("spWizardStepLabel");
    if (stepLabel && stepLabel.parentNode) {
      stepLabel.parentNode.appendChild(el);
    }
  }
  el.textContent = "черновик сохранён";
  el.style.opacity = "1";
  setTimeout(function () { el.style.opacity = "0"; }, 2000);
}

function spRestoreAutosave() {
  const key = _spAutosaveKey();
  let raw;
  try { raw = localStorage.getItem(key); } catch (e) { return false; }
  if (!raw) return false;
  let data;
  try { data = JSON.parse(raw); } catch (e) { return false; }

  const form = document.getElementById("spProfileForm");
  if (!form) return false;

  Object.keys(data).forEach(function (k) {
    if (k.startsWith("_")) return;
    const el = form.elements[k];
    if (!el) return;
    if (el.type === "checkbox") {
      el.checked = data[k] === "on" || data[k] === true;
    } else if (el.type !== "file") {
      el.value = data[k];
    }
  });

  if (data._step) spSetStep(parseInt(data._step, 10) || 0);
  spIsDirty = true;
  spUpdateSaveButtonsState();
  return true;
}

function spClearAutosave() {
  try { localStorage.removeItem(_spAutosaveKey()); } catch (e) {}
}

function spInitAutosave() {
  const form = document.getElementById("spProfileForm");
  if (!form) return;

  function onFormChange() {
    clearTimeout(_spAutosaveTimer);
    _spAutosaveTimer = setTimeout(_spAutosaveToStorage, 1000);
  }
  form.addEventListener("input", onFormChange);
  form.addEventListener("change", onFormChange);
}

