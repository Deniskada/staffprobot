/**
 * Сайдбар владельца - интерактивность
 * StaffProBot
 */

class OwnerSidebar {
    constructor() {
        this.sidebar = document.querySelector('.sidebar');
        this.overlay = document.querySelector('.sidebar-overlay');
        this.toggleBtn = document.querySelector('.topbar-toggle');
        this.collapseBtn = document.querySelector('.sidebar-collapse-btn');
        this.menuItems = document.querySelectorAll('.sidebar-item');
        
        this.isExpanded = false;
        this.isPinned = false;
        this.isMobile = window.innerWidth < 768;
        this.isTablet = window.innerWidth >= 768 && window.innerWidth < 1025;
        this.isDesktop = window.innerWidth >= 1025;
        
        this.init();
    }
    
    init() {
        this.loadState();
        this.attachEventListeners();
        this.initKeyboardShortcuts();
        this.updateLayout();
        
        // Устанавливаем активный пункт меню на основе текущего URL
        this.setActiveMenuItem();
    }
    
    /**
     * Загружаем сохраненное состояние из localStorage
     */
    loadState() {
        const savedState = localStorage.getItem('ownerSidebarState');
        if (savedState) {
            const state = JSON.parse(savedState);
            this.isPinned = state.isPinned || false;
            this.isExpanded = this.isPinned;
            
            // Восстанавливаем открытые разделы
            if (state.openSections) {
                state.openSections.forEach(sectionId => {
                    const item = document.querySelector(`[data-section="${sectionId}"]`);
                    if (item) {
                        item.classList.add('open');
                    }
                });
            }
        }
        
        // На десктопе применяем pinned состояние
        if (this.isDesktop && this.isPinned) {
            this.sidebar.classList.add('pinned', 'expanded');
            this.isExpanded = true;
        }
    }
    
    /**
     * Сохраняем состояние в localStorage
     */
    saveState() {
        const openSections = Array.from(document.querySelectorAll('.sidebar-item.open'))
            .map(item => item.dataset.section)
            .filter(Boolean);
        
        const state = {
            isPinned: this.isPinned,
            openSections: openSections
        };
        
        localStorage.setItem('ownerSidebarState', JSON.stringify(state));
    }
    
    /**
     * Навешиваем обработчики событий
     */
    attachEventListeners() {
        // Кнопка toggle в топбаре
        if (this.toggleBtn) {
            this.toggleBtn.addEventListener('click', () => this.toggle());
        }
        
        // Кнопка сворачивания в сайдбаре (только десктоп)
        if (this.collapseBtn) {
            this.collapseBtn.addEventListener('click', () => this.togglePin());
        }
        
        // Overlay для закрытия на мобильных
        if (this.overlay) {
            this.overlay.addEventListener('click', () => this.close());
        }
        
        // Аккордеон для подменю
        this.menuItems.forEach(item => {
            const link = item.querySelector('.sidebar-link');
            const hasSubmenu = item.querySelector('.sidebar-submenu');
            
            if (hasSubmenu) {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.toggleSubmenu(item);
                });
            }
        });
        
        // Обработка изменения размера окна
        window.addEventListener('resize', () => this.handleResize());
        
        // Предотвращаем клик по ссылкам подменю от сворачивания меню
        const submenuLinks = document.querySelectorAll('.sidebar-submenu .sidebar-link');
        submenuLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.stopPropagation();
                // На мобильных и планшетах закрываем сайдбар после клика
                if (this.isMobile || this.isTablet) {
                    setTimeout(() => this.close(), 150);
                }
            });
        });
    }
    
    /**
     * Переключение видимости сайдбара
     */
    toggle() {
        if (this.isExpanded) {
            this.close();
        } else {
            this.open();
        }
    }
    
    /**
     * Открыть сайдбар
     */
    open() {
        this.isExpanded = true;
        this.sidebar.classList.add('expanded', 'expanding');
        
        if (this.isMobile || this.isTablet) {
            this.overlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
        
        // Убираем класс анимации после завершения
        setTimeout(() => {
            this.sidebar.classList.remove('expanding');
        }, 200);
    }
    
    /**
     * Закрыть сайдбар
     */
    close() {
        this.isExpanded = false;
        this.sidebar.classList.remove('expanded');
        
        // Сворачиваем все открытые пункты меню при сворачивании сайдбара
        this.menuItems.forEach(item => {
            item.classList.remove('open');
        });
        
        if (this.overlay) {
            this.overlay.classList.remove('active');
        }
        
        document.body.style.overflow = '';
    }
    
    /**
     * Переключить закрепление (только десктоп)
     */
    togglePin() {
        if (!this.isDesktop) return;
        
        this.isPinned = !this.isPinned;
        
        if (this.isPinned) {
            this.sidebar.classList.add('pinned', 'expanded');
            this.isExpanded = true;
        } else {
            this.sidebar.classList.remove('pinned');
            // Всегда сворачиваем при отключении pin
            this.sidebar.classList.remove('expanded');
            this.isExpanded = false;
            
            // Сворачиваем все открытые пункты меню
            this.menuItems.forEach(item => {
                item.classList.remove('open');
            });
        }
        
        this.saveState();
    }
    
    /**
     * Переключить подменю (аккордеон)
     */
    toggleSubmenu(item) {
        const isOpen = item.classList.contains('open');
        
        // На десктопе можем держать несколько открытыми
        // На мобильных - закрываем другие
        if (this.isMobile) {
            this.menuItems.forEach(i => {
                if (i !== item) {
                    i.classList.remove('open');
                }
            });
        }
        
        item.classList.toggle('open');
        this.saveState();
    }
    
    /**
     * Установить активный пункт меню
     */
    setActiveMenuItem() {
        const currentPath = window.location.pathname;
        
        // Убираем все активные классы
        document.querySelectorAll('.sidebar-link').forEach(link => {
            link.classList.remove('active');
        });
        
        // Находим соответствующий пункт меню
        const links = document.querySelectorAll('.sidebar-link[href]');
        let activeLink = null;
        let maxMatchLength = 0;
        
        links.forEach(link => {
            const href = link.getAttribute('href');
            if (currentPath.startsWith(href) && href.length > maxMatchLength) {
                maxMatchLength = href.length;
                activeLink = link;
            }
        });
        
        if (activeLink) {
            activeLink.classList.add('active');
            
            // Открываем родительское меню, если это подпункт
            const parentItem = activeLink.closest('.sidebar-item');
            if (parentItem && parentItem.querySelector('.sidebar-submenu')) {
                parentItem.classList.add('open');
            }
            
            // Открываем родительский раздел, если это вложенный пункт
            const submenu = activeLink.closest('.sidebar-submenu');
            if (submenu) {
                const parentSection = submenu.closest('.sidebar-item');
                if (parentSection) {
                    parentSection.classList.add('open');
                }
            }
        }
    }
    
    /**
     * Обработка изменения размера окна
     */
    handleResize() {
        const wasMobile = this.isMobile;
        const wasTablet = this.isTablet;
        const wasDesktop = this.isDesktop;
        
        this.isMobile = window.innerWidth < 768;
        this.isTablet = window.innerWidth >= 768 && window.innerWidth < 1025;
        this.isDesktop = window.innerWidth >= 1025;
        
        // Если перешли на другой тип устройства
        if (this.isMobile !== wasMobile || this.isTablet !== wasTablet || this.isDesktop !== wasDesktop) {
            this.updateLayout();
        }
    }
    
    /**
     * Обновить layout в зависимости от размера экрана
     */
    updateLayout() {
        if (this.isDesktop) {
            // На десктопе восстанавливаем pinned состояние
            if (this.isPinned) {
                this.sidebar.classList.add('pinned', 'expanded');
                this.isExpanded = true;
            } else {
                this.sidebar.classList.remove('expanded');
                this.isExpanded = false;
            }
            this.overlay.classList.remove('active');
            document.body.style.overflow = '';
        } else {
            // На планшете и мобильных убираем pinned
            this.sidebar.classList.remove('pinned', 'expanded');
            this.isExpanded = false;
            this.overlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    }
    
    /**
     * Клавиатурные shortcuts
     */
    initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + B - toggle сайдбара
            if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
                e.preventDefault();
                this.toggle();
            }
            
            // Escape - закрыть сайдбар на мобильных
            if (e.key === 'Escape' && (this.isMobile || this.isTablet) && this.isExpanded) {
                this.close();
            }
            
            // Cmd/Ctrl + 1-7 - быстрые переходы
            if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '7') {
                e.preventDefault();
                const shortcuts = [
                    '/owner',                    // 1 - Главная
                    '/owner/calendar',           // 2 - Планирование
                    '/owner/employees',          // 3 - Персонал
                    '/owner/objects',            // 4 - Объекты
                    '/owner/payroll',            // 5 - Финансы
                    '/owner/reviews',            // 6 - Отзывы
                    '/owner/profile'             // 7 - Настройки
                ];
                
                const index = parseInt(e.key) - 1;
                if (shortcuts[index]) {
                    window.location.href = shortcuts[index];
                }
            }
        });
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.ownerSidebar = new OwnerSidebar();
});

