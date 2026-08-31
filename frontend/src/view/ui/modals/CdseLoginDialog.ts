export type CdseLoginResult =
  | { readonly action: "submit"; readonly username: string; readonly password: string; readonly totp: string; readonly remember: boolean }
  | { readonly action: "cancel" }
  | { readonly action: "forget" };

export class CdseLoginDialog {
  private readonly overlay = document.createElement("div");
  private readonly dialog = document.createElement("div");
  private readonly usernameInput = document.createElement("input");
  private readonly passwordInput = document.createElement("input");
  private readonly totpInput = document.createElement("input");
  private readonly rememberCheckbox = document.createElement("input");
  private readonly errorRegion = document.createElement("div");
  private readonly connectBtn = document.createElement("button");
  private readonly cancelBtn = document.createElement("button");
  private readonly forgetBtn = document.createElement("button");

  private resolvePromise: ((result: CdseLoginResult) => void) | null = null;

  constructor() {
    this.overlay.style.cssText = `
      position: fixed; inset: 0; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px);
      display: flex; justify-content: center; align-items: center; z-index: 11000;
      font-family: var(--font-family-sans, sans-serif); color: var(--text-primary, #fff);
    `;

    this.dialog.style.cssText = `
      width: 420px; background: var(--color-surface, #1e1e1e); border: 1px solid var(--color-border, #333);
      border-radius: 8px; padding: 24px; display: flex; flex-direction: column; gap: 16px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    `;
    this.dialog.setAttribute("role", "dialog");
    this.dialog.setAttribute("aria-modal", "true");
    this.dialog.setAttribute("aria-labelledby", "cdse-login-title");

    const title = document.createElement("h2");
    title.id = "cdse-login-title";
    title.textContent = "Autenticació CDSE";
    title.style.cssText = "margin: 0 0 8px 0; font-size: 18px; font-weight: 600;";

    const desc = document.createElement("p");
    desc.textContent = "Aquesta descàrrega requereix accés als productes comercials de Copernicus Data Space Ecosystem. Introdueix les teves credencials.";
    desc.style.cssText = "margin: 0; font-size: 14px; color: var(--text-secondary, #aaa); line-height: 1.4;";

    this.usernameInput.type = "text";
    this.usernameInput.autocomplete = "username";
    this.usernameInput.placeholder = "Correu electrònic";
    this.usernameInput.style.cssText = `
      width: 100%; padding: 10px 12px; background: #000; border: 1px solid #333;
      border-radius: 4px; color: #fff; font-size: 14px; box-sizing: border-box;
    `;

    this.passwordInput.type = "password";
    this.passwordInput.autocomplete = "current-password";
    this.passwordInput.placeholder = "Contrasenya";
    this.passwordInput.style.cssText = this.usernameInput.style.cssText;

    this.totpInput.type = "text";
    this.totpInput.autocomplete = "one-time-code";
    this.totpInput.inputMode = "numeric";
    this.totpInput.placeholder = "Codi 2FA (només si el compte en té)";
    this.totpInput.style.cssText = this.usernameInput.style.cssText;

    this.errorRegion.setAttribute("role", "alert");
    this.errorRegion.style.cssText = "display:none;color:#fca5a5;font-size:12px;line-height:1.35";

    const rememberRow = document.createElement("label");
    rememberRow.style.cssText = "display: flex; align-items: flex-start; gap: 8px; font-size: 13px; cursor: pointer;";
    
    this.rememberCheckbox.type = "checkbox";
    this.rememberCheckbox.style.marginTop = "2px";
    
    const rememberText = document.createElement("div");
    rememberText.innerHTML = `<b>Recordar credencials en aquest dispositiu</b><br>
      <span style="color: #888; font-size: 12px;">S'utilitza el magatzem de claus segur del sistema operatiu per protegir-les (Keyring/Credential Manager). Mai es desen en text pla.</span>`;
    
    rememberRow.appendChild(this.rememberCheckbox);
    rememberRow.appendChild(rememberText);

    const actions = document.createElement("div");
    actions.style.cssText = "display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px;";

    this.cancelBtn.textContent = "Cancel·lar";
    this.cancelBtn.style.cssText = `
      padding: 8px 16px; background: transparent; border: 1px solid #444; border-radius: 4px;
      color: #fff; cursor: pointer;
    `;

    this.connectBtn.textContent = "Connectar";
    this.connectBtn.style.cssText = `
      padding: 8px 16px; background: #1976d2; border: none; border-radius: 4px;
      color: #fff; cursor: pointer; font-weight: 500;
    `;

    this.forgetBtn.textContent = "Oblidar credencials desades";
    this.forgetBtn.style.cssText = `
      padding: 8px 16px; background: transparent; border: 1px solid #f44336; border-radius: 4px;
      color: #f44336; cursor: pointer; margin-right: auto;
    `;

    actions.appendChild(this.forgetBtn);
    actions.appendChild(this.cancelBtn);
    actions.appendChild(this.connectBtn);

    this.dialog.append(title, desc, this.usernameInput, this.passwordInput, this.totpInput, this.errorRegion, rememberRow, actions);
    this.overlay.appendChild(this.dialog);

    this.connectBtn.addEventListener("click", () => this.submit());

    this.cancelBtn.addEventListener("click", () => {
      this.close({ action: "cancel" });
    });

    this.forgetBtn.addEventListener("click", () => {
      this.close({ action: "forget" });
    });

    this.dialog.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        this.submit();
      } else if (event.key === "Escape") {
        event.preventDefault();
        this.close({ action: "cancel" });
      }
    });
  }

  public prompt(): Promise<CdseLoginResult> {
    document.body.appendChild(this.overlay);
    this.usernameInput.focus();
    return new Promise((resolve) => {
      this.resolvePromise = resolve;
    });
  }

  private submit(): void {
    const username = this.usernameInput.value.trim();
    const password = this.passwordInput.value;
    const totp = this.totpInput.value.trim();
    if (!username || !password) {
      this.errorRegion.textContent = "Cal indicar el correu i la contrasenya del compte CDSE.";
      this.errorRegion.style.display = "block";
      (!username ? this.usernameInput : this.passwordInput).focus();
      return;
    }
    if (totp && !/^\d{6}$/.test(totp)) {
      this.errorRegion.textContent = "El codi 2FA ha de contenir 6 dígits.";
      this.errorRegion.style.display = "block";
      this.totpInput.focus();
      return;
    }
    this.close({
      action: "submit",
      username,
      password,
      totp,
      remember: this.rememberCheckbox.checked,
    });
  }

  private close(result: CdseLoginResult): void {
    if (this.overlay.parentNode) {
      this.overlay.parentNode.removeChild(this.overlay);
    }
    if (this.resolvePromise) {
      this.resolvePromise(result);
      this.resolvePromise = null;
    }
  }
}
