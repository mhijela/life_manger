document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    const toggle = document.getElementById('sidebarToggle');

    function openSidebar() {
        sidebar?.classList.add('show');
        backdrop?.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        sidebar?.classList.remove('show');
        backdrop?.classList.remove('show');
        document.body.style.overflow = '';
    }

    toggle?.addEventListener('click', () => {
        sidebar?.classList.contains('show') ? closeSidebar() : openSidebar();
    });

    backdrop?.addEventListener('click', closeSidebar);

    document.querySelectorAll('#sidebar .nav-link').forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth < 768) closeSidebar();
        });
    });

    document.querySelectorAll('.alert-container .alert').forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });
});

function confirmDelete(url) {
    document.getElementById('deleteForm').action = url;
    new bootstrap.Modal(document.getElementById('deleteModal')).show();
}

(function initGlobalSearch() {
    const wrap = document.getElementById('globalSearchWrap');
    const input = document.getElementById('globalSearchInput');
    const dropdown = document.getElementById('globalSearchDropdown');
    if (!wrap || !input || !dropdown) return;

    let timer = null;
    let activeIndex = -1;

    const escapeHtml = (str) => String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');

    const hideDropdown = () => {
        dropdown.classList.add('d-none');
        activeIndex = -1;
    };

    const renderResults = (data) => {
        if (!data.query || data.query.length < 2) {
            hideDropdown();
            return;
        }

        if (!data.results.length) {
            dropdown.innerHTML = '<div class="search-dropdown-empty"><i class="bi bi-search"></i> لا توجد نتائج</div>';
            dropdown.classList.remove('d-none');
            return;
        }

        let html = data.results.map((item, i) => `
            <a href="${escapeHtml(item.url)}" class="search-result-item" data-index="${i}">
                <span class="search-result-icon"><i class="bi ${escapeHtml(item.icon)}"></i></span>
                <div class="flex-grow-1 min-w-0">
                    <div class="search-result-title">${escapeHtml(item.title)}</div>
                    <div class="search-result-meta">${escapeHtml(item.subtitle)}</div>
                </div>
            </a>
        `).join('');

        if (data.total > data.results.length && data.more_url) {
            html += `<div class="search-dropdown-footer"><a href="${escapeHtml(data.more_url)}">عرض كل النتائج (${data.total})</a></div>`;
        }

        dropdown.innerHTML = html;
        dropdown.classList.remove('d-none');
    };

    const fetchResults = (q) => {
        dropdown.innerHTML = '<div class="search-dropdown-loading"><i class="bi bi-hourglass-split"></i> جاري البحث...</div>';
        dropdown.classList.remove('d-none');

        fetch(`/search/?q=${encodeURIComponent(q)}&format=json`)
            .then(r => r.json())
            .then(renderResults)
            .catch(() => hideDropdown());
    };

    input.addEventListener('input', () => {
        clearTimeout(timer);
        const q = input.value.trim();
        if (q.length < 2) {
            hideDropdown();
            return;
        }
        timer = setTimeout(() => fetchResults(q), 300);
    });

    input.addEventListener('focus', () => {
        const q = input.value.trim();
        if (q.length >= 2) fetchResults(q);
    });

    input.addEventListener('keydown', (e) => {
        const items = dropdown.querySelectorAll('.search-result-item');
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            activeIndex = Math.min(activeIndex + 1, items.length - 1);
            items.forEach((el, i) => el.classList.toggle('active', i === activeIndex));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            activeIndex = Math.max(activeIndex - 1, 0);
            items.forEach((el, i) => el.classList.toggle('active', i === activeIndex));
        } else if (e.key === 'Enter' && activeIndex >= 0 && items[activeIndex]) {
            e.preventDefault();
            window.location = items[activeIndex].href;
        } else if (e.key === 'Escape') {
            hideDropdown();
            input.blur();
        }
    });

    document.addEventListener('click', (e) => {
        if (!wrap.contains(e.target)) hideDropdown();
    });

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            input.focus();
            input.select();
        }
    });
})();
