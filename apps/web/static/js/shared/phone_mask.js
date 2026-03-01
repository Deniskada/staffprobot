// Маска ввода телефона: +7 (999) 999-99-99
(function () {
  function applyPhoneMask(input) {
    if (!input) return;

    input.addEventListener("input", handleInput);
    input.addEventListener("focus", handleFocus);
    input.addEventListener("keydown", handleKeydown);

    if (input.value && !/^\+7/.test(input.value)) {
      input.value = formatPhone(input.value);
    }
  }

  function handleFocus(e) {
    var input = e.target;
    if (!input.value) {
      input.value = "+7 (";
      setCursorPos(input, input.value.length);
    }
  }

  function handleKeydown(e) {
    if (e.key === "Backspace" && e.target.value.length <= 4) {
      e.preventDefault();
    }
  }

  function handleInput(e) {
    var input = e.target;
    var digits = input.value.replace(/\D/g, "");

    if (!digits || digits === "7") {
      input.value = "+7 (";
      return;
    }

    if (digits[0] === "8") {
      digits = "7" + digits.substring(1);
    } else if (digits[0] !== "7") {
      digits = "7" + digits;
    }

    if (digits.length > 11) {
      digits = digits.substring(0, 11);
    }

    input.value = formatDigits(digits);
  }

  function formatDigits(digits) {
    var result = "+7";
    if (digits.length > 1) result += " (" + digits.substring(1, 4);
    if (digits.length >= 4) result += ") ";
    if (digits.length > 4) result += digits.substring(4, 7);
    if (digits.length > 7) result += "-" + digits.substring(7, 9);
    if (digits.length > 9) result += "-" + digits.substring(9, 11);
    return result;
  }

  function formatPhone(value) {
    var digits = value.replace(/\D/g, "");
    if (!digits) return "";
    if (digits[0] === "8") digits = "7" + digits.substring(1);
    if (digits[0] !== "7") digits = "7" + digits;
    return formatDigits(digits);
  }

  function setCursorPos(input, pos) {
    setTimeout(function () {
      input.setSelectionRange(pos, pos);
    }, 0);
  }

  function initAll() {
    var inputs = document.querySelectorAll('input[type="tel"], input[data-phone-mask]');
    inputs.forEach(applyPhoneMask);
  }

  window.SPPhoneMask = {
    apply: applyPhoneMask,
    initAll: initAll,
  };

  document.addEventListener("DOMContentLoaded", initAll);
})();
