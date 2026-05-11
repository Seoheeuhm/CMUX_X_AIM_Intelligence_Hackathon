(function () {
  'use strict';

  // ── CSS ────────────────────────────────────────────────────────────────────
  var _css = [
    /* LOGIN MODAL */
    '#login-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:500;align-items:center;justify-content:center;padding:16px}',
    '#login-overlay.open{display:flex}',
    '#login-modal{background:#fff;border-radius:16px;padding:40px 36px 32px;width:100%;max-width:380px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.18);position:relative;animation:nbModalIn .25s ease}',
    '@keyframes nbModalIn{from{opacity:0;transform:scale(.94) translateY(12px)}to{opacity:1;transform:scale(1) translateY(0)}}',
    '#login-close{position:absolute;top:14px;right:16px;background:none;border:none;cursor:pointer;font-size:20px;color:var(--g400);line-height:1;padding:4px 8px;border-radius:6px;transition:color .15s}',
    '#login-close:hover{color:var(--g700)}',
    '.login-logo{display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:8px}',
    '.login-logo img{height:36px;width:auto}',
    '.login-logo span{font-size:18px;font-weight:800;color:var(--g900)}',
    '#login-modal h2{font-size:22px;font-weight:700;color:var(--g900);margin-bottom:6px}',
    '.login-sub{font-size:13px;color:var(--g500);margin-bottom:28px}',
    '#modal-google-btn{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;padding:13px 20px;border:1.5px solid var(--g200);border-radius:10px;background:#fff;font-size:15px;font-weight:600;color:var(--g900);text-decoration:none;cursor:pointer;transition:all .18s}',
    '#modal-google-btn:hover{border-color:var(--g400);background:var(--g50);box-shadow:0 2px 8px rgba(0,0,0,.08)}',
    '.login-footer{font-size:12px;color:var(--g400);margin-top:20px}',
    /* NAV */
    'nav.nb{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(255,255,255,.9);backdrop-filter:blur(12px);border-bottom:1px solid var(--g200);padding:14px 24px;display:flex;align-items:center;justify-content:space-between}',
    '.nb .nav-logo{display:flex;align-items:center;gap:10px;text-decoration:none}',
    '.nb .logo-img{height:40px;width:auto;flex-shrink:0}',
    '.nb .logo-name{font-size:17px;font-weight:800;color:var(--g900)}',
    '.nb .nav-links{list-style:none;display:flex;gap:28px;align-items:center}',
    '.nb .nav-links a{font-size:14px;font-weight:600;color:var(--g500);text-decoration:none;transition:color .2s;white-space:nowrap}',
    '.nb .nav-links a:hover{color:var(--g900)}',
    '.nb .nav-links a.active{color:var(--g900)}',
    '.nb .nav-right{display:flex;align-items:center;gap:12px}',
    '.nb .nav-cta{padding:8px 18px;background:var(--p);color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;text-decoration:none;transition:background .2s;display:inline-flex;align-items:center}',
    '.nb .nav-cta:hover{background:var(--pd)}',
    '.nb .nav-hamburger{display:none;background:none;border:none;cursor:pointer;font-size:18px;color:var(--g700);padding:4px}',
    '.nb-mobile{display:none;position:fixed;top:63px;left:0;right:0;z-index:99;background:#fff;border-bottom:1px solid var(--g200);padding:16px 24px;flex-direction:column;gap:0}',
    '.nb-mobile a{display:block;padding:12px 0;font-size:15px;font-weight:600;color:var(--g700);text-decoration:none;border-bottom:1px solid var(--g100)}',
    '.nb-mobile.open{display:flex}',
    '.nb-mobile .nav-mobile-cta{margin-top:12px;padding:12px 20px!important;background:var(--p);color:#fff!important;border-radius:8px;text-align:center;border:none!important}',
    '@media(max-width:768px){.nb .nav-links{display:none}.nb .nav-hamburger{display:block}}',
    /* PROFILE DROPDOWN */
    '.nav-profile{position:relative}',
    '.profile-avatar-btn{width:38px;height:38px;border-radius:50%;border:2px solid var(--g200);background:none;cursor:pointer;padding:0;overflow:hidden;transition:border-color .18s,box-shadow .18s;flex-shrink:0;display:none}',
    '.profile-avatar-btn:hover{border-color:var(--p);box-shadow:0 0 0 3px var(--pl)}',
    '.profile-avatar-btn img{width:100%;height:100%;object-fit:cover;border-radius:50%}',
    '.profile-avatar-initials{width:100%;height:100%;border-radius:50%;background:linear-gradient(135deg,var(--p),var(--pd));display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:#fff;letter-spacing:.5px}',
    '.profile-dropdown{position:absolute;top:calc(100% + 10px);right:0;width:240px;background:#fff;border:1px solid var(--g200);border-radius:14px;box-shadow:0 8px 32px rgba(0,0,0,.13),0 2px 8px rgba(0,0,0,.06);z-index:200;opacity:0;transform:translateY(-6px) scale(.97);pointer-events:none;transition:opacity .18s ease,transform .18s ease;transform-origin:top right}',
    '.profile-dropdown.open{opacity:1;transform:translateY(0) scale(1);pointer-events:auto}',
    '.pd-header{display:flex;align-items:center;gap:12px;padding:16px 16px 14px;border-bottom:1px solid var(--g100)}',
    '.pd-avatar{width:44px;height:44px;border-radius:50%;overflow:hidden;flex-shrink:0;border:2px solid var(--g200)}',
    '.pd-avatar img{width:100%;height:100%;object-fit:cover}',
    '.pd-avatar-init{width:100%;height:100%;background:linear-gradient(135deg,var(--p),var(--pd));display:flex;align-items:center;justify-content:center;font-size:17px;font-weight:700;color:#fff}',
    '.pd-info{min-width:0}',
    '.pd-name{font-size:14px;font-weight:700;color:var(--g900);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
    '.pd-email{font-size:12px;color:var(--g400);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}',
    '.pd-menu{padding:6px 0}',
    '.pd-item{display:flex;align-items:center;gap:10px;padding:10px 16px;font-size:14px;font-weight:500;color:var(--g700);text-decoration:none;cursor:pointer;background:none;border:none;width:100%;text-align:left;transition:background .13s,color .13s}',
    '.pd-item:hover{background:var(--g50);color:var(--g900)}',
    '.pd-item i{width:16px;text-align:center;color:var(--g400);font-size:13px;flex-shrink:0}',
    '.pd-divider{height:1px;background:var(--g100);margin:4px 0}',
    '.pd-item.logout{color:var(--err)}',
    '.pd-item.logout i{color:var(--err)}',
    '.pd-item.logout:hover{background:#FEF2F2}',
    '#plan-badge{font-size:12px;color:#6B7280;padding:3px 10px;background:#F3F4F6;border-radius:12px;white-space:nowrap;display:none}',
  ].join('');

  // ── HTML builder ────────────────────────────────────────────────────────────
  function _buildHTML(activePage) {
    var isHome = activePage === 'home';
    var featHref  = isHome ? '#features' : '/#features';
    var priceHref = isHome ? '#pricing'  : '/#pricing';
    function activeClass(page) { return activePage === page ? ' class="active"' : ''; }

    return (
      '<nav class="nb">' +
        '<a href="/" class="nav-logo">' +
          '<img src="/static/logo.png" class="logo-img" alt="Portfolog">' +
          '<span class="logo-name">Portfolog</span>' +
        '</a>' +
        '<ul class="nav-links">' +
          '<li><a href="' + featHref + '"' + activeClass('features') + '>기능</a></li>' +
          '<li><a href="' + priceHref + '"' + activeClass('pricing') + '>가격</a></li>' +
          '<li><a href="/docs"' + activeClass('docs') + '>문서</a></li>' +
          '<li><a href="/qna"' + activeClass('qna') + '>문의</a></li>' +
        '</ul>' +
        '<div class="nav-right">' +
          '<a id="nav-login-btn" href="#" onclick="openLoginModal();return false;" class="nav-cta">Google로 시작하기 →</a>' +
          '<span id="plan-badge"></span>' +
          '<div class="nav-profile">' +
            '<button class="profile-avatar-btn" id="profileAvatarBtn" onclick="toggleProfileDropdown()" aria-label="프로필">' +
              '<div class="profile-avatar-initials" id="profileAvatarInner"></div>' +
            '</button>' +
            '<div class="profile-dropdown" id="profileDropdown">' +
              '<div class="pd-header">' +
                '<div class="pd-avatar" id="pdAvatar"><div class="pd-avatar-init" id="pdAvatarInit"></div></div>' +
                '<div class="pd-info">' +
                  '<div class="pd-name" id="pdName"></div>' +
                  '<div class="pd-email" id="pdEmail"></div>' +
                '</div>' +
              '</div>' +
              '<div class="pd-menu">' +
                '<a href="/app" class="pd-item"><i class="fa-solid fa-wand-magic-sparkles"></i>포트폴리오 만들기</a>' +
                '<div class="pd-divider"></div>' +
                '<button class="pd-item logout" onclick="authLogout()"><i class="fa-solid fa-right-from-bracket"></i>로그아웃</button>' +
              '</div>' +
            '</div>' +
          '</div>' +
          '<button class="nav-hamburger" id="nbToggle" aria-label="메뉴"><i class="fa-solid fa-bars"></i></button>' +
        '</div>' +
      '</nav>' +
      '<div class="nb-mobile" id="nbMobile">' +
        '<a href="' + featHref + '">기능</a>' +
        '<a href="' + priceHref + '">가격</a>' +
        '<a href="/docs">문서</a>' +
        '<a href="/qna">문의</a>' +
        '<a href="#" onclick="openLoginModal();return false;" class="nav-mobile-cta">Google로 시작하기 →</a>' +
      '</div>' +
      '<div id="login-overlay" onclick="handleOverlayClick(event)">' +
        '<div id="login-modal">' +
          '<button id="login-close" onclick="closeLoginModal()" aria-label="닫기">×</button>' +
          '<div class="login-logo">' +
            '<img src="/static/logo.png" alt="Portfolog">' +
            '<span>Portfolog</span>' +
          '</div>' +
          '<h2>시작하기</h2>' +
          '<p class="login-sub">Google 계정으로 1초만에 로그인하세요</p>' +
          '<a href="/auth/login" id="modal-google-btn">' +
            '<svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">' +
              '<path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>' +
              '<path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>' +
              '<path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>' +
              '<path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>' +
            '</svg>' +
            'Google로 계속하기' +
          '</a>' +
          '<p class="login-footer">계정이 없으면 자동으로 가입됩니다</p>' +
        '</div>' +
      '</div>'
    );
  }

  // ── Internal logic ──────────────────────────────────────────────────────────
  function _parseJWT(token) {
    try { return JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))); }
    catch (e) { return {}; }
  }

  function _setAvatar(containerEl, initEl, avatarUrl, initials) {
    if (avatarUrl) {
      var img = document.createElement('img');
      img.src = avatarUrl;
      img.alt = '';
      img.onerror = function () { img.remove(); initEl.textContent = initials; };
      containerEl.prepend(img);
      initEl.style.display = 'none';
    } else {
      initEl.textContent = initials;
    }
  }

  function _updateNav() {
    var token = localStorage.getItem('sb_access_token');
    var loginBtn = document.getElementById('nav-login-btn');
    var avatarBtn = document.getElementById('profileAvatarBtn');
    var planBadge = document.getElementById('plan-badge');

    if (!token) {
      if (loginBtn) loginBtn.style.display = 'inline-flex';
      if (avatarBtn) avatarBtn.style.display = 'none';
      if (planBadge) planBadge.style.display = 'none';
      return;
    }

    if (loginBtn) loginBtn.style.display = 'none';
    if (avatarBtn) avatarBtn.style.display = 'flex';

    var heroCta = document.getElementById('hero-cta-btn');
    if (heroCta) { heroCta.textContent = '포트폴리오 만들기 →'; heroCta.href = '/app'; heroCta.removeAttribute('onclick'); }

    var ctaBtn = document.getElementById('cta-bottom-btn');
    if (ctaBtn) { ctaBtn.textContent = '포트폴리오 만들기 →'; ctaBtn.href = '/app'; ctaBtn.removeAttribute('onclick'); }

    var payload = _parseJWT(token);
    var meta = payload.user_metadata || {};
    var email = payload.email || meta.email || '';
    var fullName = meta.full_name || meta.name || email.split('@')[0] || '?';
    var avatarUrl = meta.avatar_url || meta.picture || '';
    var initials = fullName.split(' ').map(function (w) { return w[0]; }).join('').slice(0, 2).toUpperCase() || '?';

    _setAvatar(document.getElementById('profileAvatarInner').parentElement,
               document.getElementById('profileAvatarInner'), avatarUrl, initials);

    document.getElementById('pdName').textContent = fullName;
    document.getElementById('pdEmail').textContent = email;
    _setAvatar(document.getElementById('pdAvatar'), document.getElementById('pdAvatarInit'), avatarUrl, initials);
  }

  // ── Global API ──────────────────────────────────────────────────────────────
  window.authLogout = function () {
    localStorage.removeItem('sb_access_token');
    localStorage.removeItem('sb_refresh_token');
    window.location.href = '/';
  };

  window.openLoginModal = function () {
    var el = document.getElementById('login-overlay');
    if (el) { el.classList.add('open'); document.body.style.overflow = 'hidden'; }
  };

  window.closeLoginModal = function () {
    var el = document.getElementById('login-overlay');
    if (el) { el.classList.remove('open'); document.body.style.overflow = ''; }
  };

  window.handleOverlayClick = function (e) {
    if (e.target === document.getElementById('login-overlay')) window.closeLoginModal();
  };

  window.toggleProfileDropdown = function () {
    var dd = document.getElementById('profileDropdown');
    if (dd) dd.classList.toggle('open');
  };

  window.updateNav = _updateNav;

  // ── Init ────────────────────────────────────────────────────────────────────
  window.initNavbar = function (opts) {
    opts = opts || {};
    var activePage = opts.activePage || '';

    // 1. Inject CSS
    var styleEl = document.createElement('style');
    styleEl.textContent = _css;
    document.head.appendChild(styleEl);

    // 2. Inject HTML at top of body
    var tmp = document.createElement('div');
    tmp.innerHTML = _buildHTML(activePage);
    while (tmp.firstChild) {
      document.body.insertBefore(tmp.firstChild, document.body.firstChild);
    }

    // 3. Body padding for pages with fixed nav (non-landing)
    if (opts.addBodyPadding) {
      document.body.style.paddingTop = '63px';
    }

    // 4. Hamburger toggle
    var toggle = document.getElementById('nbToggle');
    var mobile = document.getElementById('nbMobile');
    if (toggle && mobile) {
      toggle.addEventListener('click', function () { mobile.classList.toggle('open'); });
      mobile.querySelectorAll('a').forEach(function (a) {
        a.addEventListener('click', function () { mobile.classList.remove('open'); });
      });
    }

    // 5. Click-outside closes dropdown
    document.addEventListener('click', function (e) {
      var btn = document.getElementById('profileAvatarBtn');
      var dd = document.getElementById('profileDropdown');
      if (dd && btn && !dd.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
        dd.classList.remove('open');
      }
    });

    // 6. Escape closes modal
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') window.closeLoginModal();
    });

    // 7. Run updateNav on DOM ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () {
        _updateNav();
        if (new URLSearchParams(window.location.search).get('auth_required')) window.openLoginModal();
      });
    } else {
      _updateNav();
      if (new URLSearchParams(window.location.search).get('auth_required')) window.openLoginModal();
    }
  };
})();
