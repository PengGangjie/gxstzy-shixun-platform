/*! 实训科平台 · 游客门禁：首页可看，模块/搜索/驾驶舱明细需登录 */
(function () {
  const SIGN_IN = "/sign-in";
  const MODULE_RE =
    /(platform-\d+|实训室安全数据驾驶舱|实训室分级分类台账|lab-grade-boards)/i;

  function isModuleHref(href) {
    if (!href || href.startsWith("http") || href.startsWith("mailto:")) return false;
    try {
      const u = new URL(href, location.origin);
      if (u.origin !== location.origin) return false;
      return MODULE_RE.test(u.pathname) || MODULE_RE.test(href);
    } catch (_) {
      return MODULE_RE.test(href);
    }
  }

  function toSignIn(nextPath) {
    const next = nextPath && nextPath.startsWith("/") ? nextPath : location.pathname;
    location.href = SIGN_IN + "?next=" + encodeURIComponent(next);
  }

  function ensureStyles() {
    if (document.getElementById("guest-gate-style")) return;
    const s = document.createElement("style");
    s.id = "guest-gate-style";
    s.textContent = `
      .guest-auth-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-left:auto}
      .guest-auth-bar .guest-btn{display:inline-flex;align-items:center;justify-content:center;min-height:36px;padding:0 14px;border-radius:4px;font-size:13px;border:1px solid rgba(255,255,255,.35);background:#fff;color:#005c2d!important;cursor:pointer;text-decoration:none}
      .guest-auth-bar .guest-btn.primary{background:#FFFA00;border-color:#e6e000;color:#191919!important;font-weight:600}
      .guest-auth-bar .guest-user{font-size:13px;color:#fff;opacity:.95}
      .guest-lock-banner{margin:12px 0 16px;padding:12px 14px;background:#fff8e1;border:1px solid #ffe082;border-radius:6px;font-size:14px;color:#6d4c00}
      .guest-lock-banner a{color:#008742;font-weight:600}
      .guest-search-locked .text{background:#f5f5f5;cursor:not-allowed}
      .guest-cockpit-lock{padding:36px 20px;text-align:center;background:#f8fbf9;border:1px dashed #c8e6d0;border-radius:8px;color:#555}
      .guest-cockpit-lock a{display:inline-block;margin-top:12px;padding:8px 18px;background:#008742;color:#fff!important;border-radius:4px}
      body.guest-mode .navbar a[href*="platform-"],
      body.guest-mode .portal-btns a,
      body.guest-mode .link-top a[href*="驾驶舱"],
      body.guest-mode .link-top a[href*="信息牌"]{opacity:.72}
    `;
    document.head.appendChild(s);
  }

  function mountAuthBar(me) {
    const web = document.querySelector(".link-top .web");
    if (!web || document.getElementById("guest-auth-bar")) return;
    const bar = document.createElement("div");
    bar.id = "guest-auth-bar";
    bar.className = "guest-auth-bar";
    if (me && me.authenticated) {
      const label = me.role_label || "已登录";
      const name = me.email || me.name || "";
      bar.innerHTML =
        '<span class="guest-user">' +
        label +
        (name ? " · " + name : "") +
        "</span>" +
        (me.admin_panel
          ? '<a class="guest-btn" href="' + me.admin_panel + '">权限后台</a>'
          : "") +
        '<a class="guest-btn" href="/sign-out">退出</a>';
    } else {
      bar.innerHTML =
        '<a class="guest-btn primary" href="' +
        SIGN_IN +
        "?next=" +
        encodeURIComponent(location.pathname || "/") +
        '">登录后解锁全部功能</a>';
    }
    web.appendChild(bar);
  }

  function lockGuestUi() {
    document.body.classList.add("guest-mode");
    const intro = document.querySelector(".list-con .web > p");
    if (intro && !document.getElementById("guest-lock-banner")) {
      const ban = document.createElement("div");
      ban.id = "guest-lock-banner";
      ban.className = "guest-lock-banner";
      ban.innerHTML =
        '当前为<strong>游客浏览</strong>：可查看首页介绍。七大业务模块、全站搜索与驾驶舱明细需' +
        '<a href="' +
        SIGN_IN +
        "?next=/'" +
        ">登录</a>" +
        "后解锁。";
      intro.insertAdjacentElement("afterend", ban);
    }

    const box = document.querySelector(".searchbox");
    const input = document.getElementById("banner-search");
    const form = document.getElementById("banner-search-form");
    if (box) box.classList.add("guest-search-locked");
    if (input) {
      input.readOnly = true;
      input.placeholder = "登录后使用搜索";
      input.title = "请先登录";
    }
    if (form) {
      form.addEventListener(
        "submit",
        function (e) {
          e.preventDefault();
          e.stopImmediatePropagation();
          toSignIn("/");
        },
        true
      );
    }
    if (input) {
      input.addEventListener(
        "focus",
        function (e) {
          e.preventDefault();
          input.blur();
          toSignIn("/");
        },
        true
      );
    }

    document.addEventListener(
      "click",
      function (e) {
        const a = e.target.closest && e.target.closest("a[href]");
        if (!a) return;
        const href = a.getAttribute("href") || "";
        if (isModuleHref(href)) {
          e.preventDefault();
          e.stopPropagation();
          try {
            const u = new URL(href, location.origin);
            toSignIn(u.pathname + u.search + u.hash);
          } catch (_) {
            toSignIn("/");
          }
        }
      },
      true
    );

    const cockpit = document.getElementById("cockpit-root") || document.getElementById("cockpit-mount");
    if (cockpit) {
      cockpit.innerHTML =
        '<div class="guest-cockpit-lock"><p>安全数据驾驶舱明细需登录后查看</p>' +
        '<a href="' +
        SIGN_IN +
        '?next=/">登录解锁</a></div>';
    }
    ["lab-baseline-data", "lab-docs-stats-data"].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.textContent = "{}";
    });
  }

  async function boot() {
    ensureStyles();
    let me = { authenticated: false };
    try {
      const res = await fetch("/api/me", { credentials: "same-origin" });
      me = await res.json();
    } catch (_) {}
    mountAuthBar(me);
    if (!me || !me.authenticated) lockGuestUi();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
