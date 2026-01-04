/**
 * SOVRN MML - Interactive System
 * Generated JavaScript
 */

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initCursor();
    initNavigation();
    initProjects();
    initTime();
    initGridOverlay();
    initForm();
    initScrollAnimations();
});

// ============================================
// CUSTOM CURSOR
// ============================================

function initCursor() {
    const cursor = document.querySelector('.cursor');
    const follower = document.querySelector('.cursor-follower');
    
    if (!cursor) return;
    
    let mouseX = 0, mouseY = 0;
    let cursorX = 0, cursorY = 0;
    let followerX = 0, followerY = 0;
    
    // Track mouse position
    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });
    
    // Smooth animation loop
    function animate() {
        // Cursor follows faster
        cursorX += (mouseX - cursorX) * 0.15;
        cursorY += (mouseY - cursorY) * 0.15;
        
        // Follower is slower (trailing effect)
        followerX += (mouseX - followerX) * 0.08;
        followerY += (mouseY - followerY) * 0.08;
        
        cursor.style.left = cursorX + 'px';
        cursor.style.top = cursorY + 'px';
        
        if (follower) {
            follower.style.left = followerX + 'px';
            follower.style.top = followerY + 'px';
        }
        
        requestAnimationFrame(animate);
    }
    
    animate();
    
    // Hover effects on interactive elements
    const hoverTargets = document.querySelectorAll(
        'a, button, .project-card, .nav-link, .principle, .publication-item, [data-hover]'
    );
    
    hoverTargets.forEach(el => {
        el.addEventListener('mouseenter', () => cursor.classList.add('active'));
        el.addEventListener('mouseleave', () => cursor.classList.remove('active'));
    });
    
    // Hide cursor when leaving window
    document.addEventListener('mouseleave', () => {
        cursor.style.opacity = '0';
        if (follower) follower.style.opacity = '0';
    });
    
    document.addEventListener('mouseenter', () => {
        cursor.style.opacity = '1';
        if (follower) follower.style.opacity = '1';
    });
}

// ============================================
// NAVIGATION
// ============================================

function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.section');
    const scrollIndicator = document.querySelector('.scroll-indicator');
    
    // Smooth scroll on nav click
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href');
            const target = document.querySelector(targetId);
            
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Scroll indicator click
    if (scrollIndicator) {
        scrollIndicator.addEventListener('click', (e) => {
            e.preventDefault();
            const href = scrollIndicator.getAttribute('href');
            const target = document.querySelector(href) || sections[1];
            
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
    
    // Active state on scroll
    let ticking = false;
    
    function updateActiveNav() {
        const scrollPos = window.scrollY + 150;
        
        sections.forEach((section, index) => {
            const top = section.offsetTop;
            const height = section.offsetHeight;
            
            if (scrollPos >= top && scrollPos < top + height) {
                navLinks.forEach(link => link.classList.remove('active'));
                if (navLinks[index]) {
                    navLinks[index].classList.add('active');
                }
            }
        });
    }
    
    window.addEventListener('scroll', () => {
        if (!ticking) {
            requestAnimationFrame(() => {
                updateActiveNav();
                ticking = false;
            });
            ticking = true;
        }
    });
    
    // Initial state
    updateActiveNav();
}

// ============================================
// PROJECTS
// ============================================

const projectsData = [
    {
        "id": 1,
        "title": "BRAND REFRESH",
        "category": "Branding",
        "year": "2024",
        "location": "Global",
        "description": "A groundbreaking project in branding."
    },
    {
        "id": 2,
        "title": "PRODUCT LAUNCH",
        "category": "Campaign",
        "year": "2024",
        "location": "Global",
        "description": "A groundbreaking project in campaign."
    },
    {
        "id": 3,
        "title": "WEB PLATFORM",
        "category": "Development",
        "year": "2023",
        "location": "Global",
        "description": "A groundbreaking project in development."
    }
];

function initProjects() {
    const container = document.querySelector('.projects-container');
    const viewBtns = document.querySelectorAll('.view-btn');
    const projectCards = document.querySelectorAll('.project-card');
    
    if (!container) return;
    
    // View toggle
    viewBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            
            viewBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            container.classList.remove('grid-view', 'list-view');
            container.classList.add(view + '-view');
        });
    });
    
    // Project click - open modal
    projectCards.forEach((card, index) => {
        card.addEventListener('click', () => {
            const project = projectsData[index] || {
                title: 'Project',
                category: 'Design',
                year: '2024',
                location: 'Global',
                description: 'A remarkable project.'
            };
            
            openProjectModal(project, index + 1);
        });
    });
}

function openProjectModal(project, number) {
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'project-modal';
    modal.innerHTML = `
        <div class="modal-backdrop"></div>
        <div class="modal-container">
            <button class="modal-close" aria-label="Close modal">×</button>
            <div class="modal-grid">
                <div class="modal-image">
                    <div class="image-placeholder concrete-texture"></div>
                </div>
                <div class="modal-content">
                    <span class="modal-number">${String(number).padStart(2, '0')}</span>
                    <h2 class="modal-title">${project.title}</h2>
                    <p class="modal-description">${project.description}</p>
                    <div class="modal-meta">
                        <div class="meta-item">
                            <span class="meta-label">CATEGORY</span>
                            <span class="meta-value">${project.category}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">YEAR</span>
                            <span class="meta-value">${project.year}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">LOCATION</span>
                            <span class="meta-value">${project.location}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
    
    // Animate in
    requestAnimationFrame(() => {
        modal.classList.add('active');
    });
    
    // Close handlers
    const close = () => {
        modal.classList.remove('active');
        setTimeout(() => {
            modal.remove();
            document.body.style.overflow = '';
        }, 300);
    };
    
    modal.querySelector('.modal-close').addEventListener('click', close);
    modal.querySelector('.modal-backdrop').addEventListener('click', close);
    
    // ESC key
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            close();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

// Inject modal styles
const modalStyles = document.createElement('style');
modalStyles.textContent = `
    .project-modal {
        position: fixed;
        inset: 0;
        z-index: 10000;
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.3s ease, visibility 0.3s ease;
    }
    
    .project-modal.active {
        opacity: 1;
        visibility: visible;
    }
    
    .modal-backdrop {
        position: absolute;
        inset: 0;
        background: rgba(0, 0, 0, 0.9);
    }
    
    .modal-container {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) scale(0.95);
        width: 90%;
        max-width: 1000px;
        max-height: 90vh;
        background: var(--color-bg, #fff);
        overflow: hidden;
        transition: transform 0.3s ease;
    }
    
    .project-modal.active .modal-container {
        transform: translate(-50%, -50%) scale(1);
    }
    
    .modal-close {
        position: absolute;
        top: 20px;
        right: 20px;
        width: 44px;
        height: 44px;
        font-size: 28px;
        background: transparent;
        border: 2px solid var(--color-text, #111);
        color: var(--color-text, #111);
        z-index: 10;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    
    .modal-close:hover {
        background: var(--color-accent, #FF3300);
        border-color: var(--color-accent, #FF3300);
        color: white;
    }
    
    .modal-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
    }
    
    .modal-image {
        min-height: 400px;
    }
    
    .modal-image .image-placeholder {
        height: 100%;
    }
    
    .modal-content {
        padding: 48px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        border-left: 3px solid var(--color-text, #111);
    }
    
    .modal-number {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.2em;
        color: var(--color-accent, #FF3300);
        margin-bottom: 16px;
    }
    
    .modal-title {
        font-size: 32px;
        font-weight: 900;
        letter-spacing: -0.02em;
        margin-bottom: 20px;
    }
    
    .modal-description {
        font-size: 14px;
        line-height: 1.7;
        color: var(--color-muted, #888);
        margin-bottom: 40px;
    }
    
    .modal-meta {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 24px;
    }
    
    .meta-item {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    
    .meta-label {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.2em;
        color: var(--color-muted, #888);
    }
    
    .meta-value {
        font-size: 14px;
        font-weight: 500;
    }
    
    @media (max-width: 768px) {
        .modal-grid {
            grid-template-columns: 1fr;
        }
        
        .modal-image {
            min-height: 200px;
        }
        
        .modal-content {
            padding: 32px 24px;
            border-left: none;
            border-top: 3px solid var(--color-text, #111);
        }
        
        .modal-meta {
            grid-template-columns: 1fr;
            gap: 16px;
        }
    }
`;
document.head.appendChild(modalStyles);

// ============================================
// TIME DISPLAY
// ============================================

function initTime() {
    const timeEl = document.getElementById('current-time');
    if (!timeEl) return;
    
    function updateTime() {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const mins = String(now.getMinutes()).padStart(2, '0');
        const secs = String(now.getSeconds()).padStart(2, '0');
        timeEl.textContent = `${hours}:${mins}:${secs}`;
    }
    
    updateTime();
    setInterval(updateTime, 1000);
}

// ============================================
// GRID OVERLAY (Debug)
// ============================================

function initGridOverlay() {
    const overlay = document.querySelector('.grid-overlay');
    if (!overlay) return;
    
    document.addEventListener('keydown', (e) => {
        // Press 'G' to toggle grid
        if (e.key.toLowerCase() === 'g' && !e.ctrlKey && !e.metaKey && !e.altKey) {
            overlay.classList.toggle('visible');
        }
    });
}

// ============================================
// CONTACT FORM
// ============================================

function initForm() {
    const form = document.querySelector('.contact-form');
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const submitBtn = form.querySelector('.form-submit');
        const originalHTML = submitBtn.innerHTML;
        
        // Loading state
        submitBtn.innerHTML = '<span>SENDING...</span>';
        submitBtn.disabled = true;
        
        // Collect data
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        // Simulate API call (replace with real endpoint)
        try {
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Success
            submitBtn.innerHTML = '<span>SENT ✓</span>';
            submitBtn.style.background = 'var(--color-accent, #00AA55)';
            
            form.reset();
            
            // Reset after delay
            setTimeout(() => {
                submitBtn.innerHTML = originalHTML;
                submitBtn.style.background = '';
                submitBtn.disabled = false;
            }, 3000);
            
        } catch (error) {
            // Error
            submitBtn.innerHTML = '<span>ERROR - TRY AGAIN</span>';
            submitBtn.style.background = '#CC0000';
            
            setTimeout(() => {
                submitBtn.innerHTML = originalHTML;
                submitBtn.style.background = '';
                submitBtn.disabled = false;
            }, 3000);
        }
    });
}

// ============================================
// SCROLL ANIMATIONS
// ============================================

function initScrollAnimations() {
    const animateElements = document.querySelectorAll(
        '.project-card, .principle, .publication-item, .statement-main'
    );
    
    if (!animateElements.length) return;
    
    // Set initial state
    animateElements.forEach((el, i) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = `opacity 0.6s ease ${i * 0.05}s, transform 0.6s ease ${i * 0.05}s`;
    });
    
    // Intersection Observer
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    });
    
    animateElements.forEach(el => observer.observe(el));
}

// ============================================
// EXPORTS
// ============================================

window.MML = {
    initCursor,
    initNavigation,
    initProjects,
    openProjectModal,
    initTime,
    initGridOverlay,
    initForm,
    initScrollAnimations
};
