/*! 实验室管理平台 · 顶栏：单行布局 + 手机抽屉 */
(function () {
  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function ensureDrawer(web, nav) {
    if (qs("#topbar-drawer")) return qs("#topbar-drawer");
    const drawer = document.createElement("div");
    drawer.id = "topbar-drawer";
    drawer.className = "topbar-drawer";
    drawer.hidden = true;
    drawer.setAttribute("role", "dialog");
    drawer.setAttribute("aria-label", "快捷入口");
    const list = document.createElement("ul");
    list.className = "topbar-drawer-list";
    nav.querySelectorAll("a").forEach(function (a) {
      const li = document.createElement("li");
      const clone = a.cloneNode(true);
      clone.removeAttribute("target");
      li.appendChild(clone);
      list.appendChild(li);
    });
    drawer.appendChild(list);
    web.appendChild(drawer);
    return drawer;
  }

  function ensureMenuBtn(web, brand, drawer) {
    if (qs("#topbar-menu-btn")) return qs("#topbar-menu-btn");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.id = "topbar-menu-btn";
    btn.className = "topbar-menu-btn";
    btn.setAttribute("aria-label", "菜单");
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-controls", "topbar-drawer");
    btn.innerHTML = "<span></span><span></span><span></span>";
    if (brand && brand.nextSibling) web.insertBefore(btn, brand.nextSibling);
    else web.insertBefore(btn, web.firstChild);

    function close() {
      drawer.hidden = true;
      btn.setAttribute("aria-expanded", "false");
      btn.classList.remove("is-open");
      document.body.classList.remove("topbar-drawer-open");
    }
    function open() {
      drawer.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      btn.classList.add("is-open");
      document.body.classList.add("topbar-drawer-open");
    }
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      if (drawer.hidden) open();
      else close();
    });
    document.addEventListener("click", function (e) {
      if (drawer.hidden) return;
      if (drawer.contains(e.target) || btn.contains(e.target)) return;
      close();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") close();
    });
    return btn;
  }

  function init() {
    const web = qs(".link-top .web");
    const nav = qs(".link-top ul.nav-links");
    if (!web || !nav) return;
    web.classList.add("topbar-ready");
    const brand = qs(".product-brand", web);
    const drawer = ensureDrawer(web, nav);
    ensureMenuBtn(web, brand, drawer);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
