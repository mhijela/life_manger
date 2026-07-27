(function () {
    var nav = document.getElementById('siteNav');
    var toggle = document.getElementById('navToggle');
    var links = document.getElementById('ztNavLinks');

    function onScroll() {
        if (!nav) return;
        nav.classList.toggle('is-scrolled', window.scrollY > 12);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    if (toggle && links) {
        toggle.addEventListener('click', function () {
            var open = links.classList.toggle('is-open');
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
        links.querySelectorAll('a').forEach(function (a) {
            a.addEventListener('click', function () {
                links.classList.remove('is-open');
                toggle.setAttribute('aria-expanded', 'false');
            });
        });
    }

    var revealItems = document.querySelectorAll('.reveal');
    if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.16 });
        revealItems.forEach(function (el) { io.observe(el); });
    } else {
        revealItems.forEach(function (el) { el.classList.add('is-visible'); });
    }

    var counted = false;
    function animateCounters() {
        if (counted) return;
        counted = true;
        document.querySelectorAll('[data-count]').forEach(function (el) {
            var target = parseInt(el.getAttribute('data-count'), 10) || 0;
            var suffix = el.getAttribute('data-suffix') || '';
            var start = 0;
            var duration = 1200;
            var t0 = null;
            function step(ts) {
                if (!t0) t0 = ts;
                var p = Math.min((ts - t0) / duration, 1);
                var val = Math.floor(start + (target - start) * p);
                el.textContent = val + suffix;
                if (p < 1) requestAnimationFrame(step);
            }
            requestAnimationFrame(step);
        });
    }

    var stats = document.querySelector('.zt-stats');
    if (stats && 'IntersectionObserver' in window) {
        var sio = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    animateCounters();
                    sio.disconnect();
                }
            });
        }, { threshold: 0.35 });
        sio.observe(stats);
    } else if (stats) {
        animateCounters();
    }

    var sections = ['top', 'about', 'services', 'work', 'why', 'contact'];
    var navAnchors = links ? Array.prototype.slice.call(links.querySelectorAll('a[href^="#"]')) : [];
    function setActiveNav() {
        var current = 'top';
        sections.forEach(function (id) {
            var el = document.getElementById(id);
            if (!el) return;
            var top = el.getBoundingClientRect().top;
            if (top <= 120) current = id;
        });
        navAnchors.forEach(function (a) {
            var href = a.getAttribute('href') || '';
            a.classList.toggle('is-active', href === '#' + current);
        });
    }
    window.addEventListener('scroll', setActiveNav, { passive: true });
    setActiveNav();
})();
